"""
Tree of Thought Synthesizer - Multi-branch synthesis for complex queries.

Generates 3 candidate syntheses in parallel through cost/talent/risk lenses,
scores each via the existing self-critique, and selects the strongest branch.
Falls back to linear synthesis on any failure.

Activated via ENABLE_TOT_SYNTHESIS flag and only for queries that completed
3 pillar workers (cost + talent + risk).
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


LENS_PROMPTS: Dict[str, str] = {
    "cost": (
        "You are synthesizing through a COST-OPTIMIZATION lens.\n"
        "Lead with cost factors: lease rates, opex, capex, tax incentives, "
        "total occupancy cost. Frame the recommendation in terms of financial "
        "efficiency. Cite every claim. Note explicitly where evidence is thin."
    ),
    "talent": (
        "You are synthesizing through a TALENT-AVAILABILITY lens.\n"
        "Lead with workforce factors: labor pool size, wages, commute, "
        "education, talent pipeline quality. Frame the recommendation in "
        "terms of human capital access. Cite every claim. Note gaps."
    ),
    "risk": (
        "You are synthesizing through a RISK-MINIMIZATION lens.\n"
        "Lead with risk factors: market volatility, regulatory environment, "
        "climate exposure, competitive saturation. Frame the recommendation "
        "in terms of downside protection. Cite every claim. Note gaps."
    ),
}

PRUNE_THRESHOLD: float = 0.5
TIE_THRESHOLD: float = 0.1
BRANCH_TIMEOUT_S: float = 60.0
MAX_EVIDENCE_CHARS: int = 4000


@dataclass
class TOTBranch:
    """A single branch in the tree of thought."""
    branch_id: str
    lens: str
    thought: str = ""
    score: float = 0.0
    relevance: float = 0.0
    support: float = 0.0
    usefulness: float = 0.0
    reasoning: str = ""
    is_pruned: bool = False
    error: Optional[str] = None


@dataclass
class TOTResult:
    """Outcome of a ToT synthesis run."""
    selected_branch: Optional[TOTBranch] = None
    runner_up: Optional[TOTBranch] = None
    all_branches: List[TOTBranch] = field(default_factory=list)
    final_response: str = ""
    method: str = "tot"


async def _generate_branch_thought(
    lens: str,
    query: str,
    evidence_block: str,
    llm_call: Callable[[str, str, Optional[int]], str],
) -> str:
    """Generate a synthesis through a specific lens."""
    lens_instruction = LENS_PROMPTS.get(lens, "")
    system = (
        f"{lens_instruction}\n\n"
        "Synthesize the evidence below into a recommendation. "
        "Use [Source: file, page] citations for every factual claim. "
        "If the evidence does not support a confident answer through this lens, "
        "say so explicitly rather than guessing."
    )
    user = (
        f"Query: {query}\n\n"
        f"Worker Evidence:\n{evidence_block}\n\n"
        f"Produce your synthesis through the {lens} lens."
    )
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, llm_call, system, user, 2000)


async def _score_branch(
    branch: TOTBranch,
    query: str,
    sources: List[Dict[str, Any]],
    llm_call: Callable[[str, str, Optional[int]], str],
    self_critique_fn: Callable[..., Awaitable[Any]],
) -> TOTBranch:
    """Score a branch using the self-critique mechanism."""
    try:
        critique = await self_critique_fn(query, branch.thought, sources, llm_call)
        branch.score = critique.score
        branch.relevance = critique.relevance
        branch.support = critique.support
        branch.usefulness = critique.usefulness
        branch.reasoning = critique.reasoning or ""
        if branch.score < PRUNE_THRESHOLD:
            branch.is_pruned = True
            logger.info(
                f"[TOT] Branch '{branch.branch_id}' pruned (score={branch.score:.2f})"
            )
        else:
            logger.info(
                f"[TOT] Branch '{branch.branch_id}' score={branch.score:.2f}"
            )
    except Exception as e:
        logger.warning(f"[TOT] Branch '{branch.branch_id}' scoring failed: {e}")
        branch.is_pruned = True
        branch.error = str(e)[:200]
    return branch


async def _run_single_branch(
    lens: str,
    query: str,
    evidence_block: str,
    sources: List[Dict[str, Any]],
    llm_call: Callable[[str, str, Optional[int]], str],
    self_critique_fn: Callable[..., Awaitable[Any]],
) -> TOTBranch:
    """Execute a single ToT branch: generate thought + score it."""
    branch = TOTBranch(branch_id=lens, lens=lens)
    try:
        async def _generate_and_score():
            branch.thought = await _generate_branch_thought(
                lens, query, evidence_block, llm_call,
            )
            return await _score_branch(
                branch, query, sources, llm_call, self_critique_fn,
            )

        await asyncio.wait_for(_generate_and_score(), timeout=BRANCH_TIMEOUT_S)
    except asyncio.TimeoutError:
        logger.warning(f"[TOT] Branch '{lens}' timed out after {BRANCH_TIMEOUT_S}s")
        branch.is_pruned = True
        branch.error = "timeout"
    except Exception as e:
        logger.warning(f"[TOT] Branch '{lens}' failed: {e}")
        branch.is_pruned = True
        branch.error = str(e)[:200]
    return branch


def _select_winner(
    branches: List[TOTBranch],
) -> Tuple[Optional[TOTBranch], Optional[TOTBranch]]:
    """Select winner and optional runner-up from scored branches."""
    survivors = [b for b in branches if not b.is_pruned]
    if not survivors:
        return None, None
    survivors.sort(key=lambda b: b.score, reverse=True)
    winner = survivors[0]
    runner_up = None
    if len(survivors) >= 2 and (winner.score - survivors[1].score) <= TIE_THRESHOLD:
        runner_up = survivors[1]
    return winner, runner_up


def _format_combined_response(winner: TOTBranch, runner_up: TOTBranch) -> str:
    """Format response when two branches are within tie threshold."""
    return (
        f"### Recommendation (primary lens: {winner.lens})\n\n"
        f"{winner.thought}\n\n"
        f"---\n\n"
        f"### Alternative view (lens: {runner_up.lens})\n\n"
        f"_This alternative scored within {TIE_THRESHOLD} of the primary "
        f"recommendation and is presented for analyst judgment._\n\n"
        f"{runner_up.thought}"
    )


def should_use_tot(state: Any) -> bool:
    """Gate ToT activation: require ≥3 completed pillar workers."""
    try:
        from agent_state import StepAction, StepStatus
        worker_actions = {
            StepAction.WORKER_COST,
            StepAction.WORKER_TALENT,
            StepAction.WORKER_RISK,
        }
        completed = sum(
            1 for step in state.plan
            if step.action in worker_actions and step.status == StepStatus.COMPLETED
        )
        return completed >= 3
    except Exception:
        return False


def build_evidence_block(state: Any, max_chars: int = MAX_EVIDENCE_CHARS) -> str:
    """Compact worker + non-worker evidence into a citation-tagged string."""
    try:
        from agent_state import StepAction, StepStatus
        worker_actions = {
            StepAction.WORKER_COST,
            StepAction.WORKER_TALENT,
            StepAction.WORKER_RISK,
        }
        parts: List[str] = []
        for step in state.plan:
            if (
                step.action in worker_actions
                and step.status == StepStatus.COMPLETED
                and step.result
            ):
                wo = step.result.get("worker_output")
                if not isinstance(wo, dict):
                    continue
                section = wo.get("section") or step.action.value
                parts.append(f"### {section}")
                for c in (wo.get("claims") or [])[:6]:
                    cite = ", ".join((c.get("citations") or [])[:2])
                    parts.append(f"- {c.get('text', '')[:300]} [{cite}]")
                for m in (wo.get("metrics") or [])[:6]:
                    cite = ", ".join((m.get("citations") or [])[:2])
                    parts.append(f"- {m.get('name', '?')} = {m.get('value', '?')} [{cite}]")
                missing = (wo.get("missing_data") or [])[:3]
                if missing:
                    parts.append(f"  (missing: {'; '.join(missing)})")
                parts.append("")

        # Include non-worker retrieved sources
        all_sources = []
        try:
            all_sources = state.memory.get_all_sources() or []
        except Exception:
            all_sources = []
        if all_sources:
            parts.append("### Additional Retrieved Evidence")
            for s in all_sources[:12]:
                src = s.get("source_file", "unknown")
                page = s.get("page_number") or s.get("page_numbers") or "?"
                text = (s.get("text") or s.get("text_snippet") or "")[:260]
                if text:
                    parts.append(f"- [{src}:{page}] {text}")
            parts.append("")

        block = "\n".join(parts).strip()
        if not block:
            return "(no worker evidence available)"
        if len(block) > max_chars:
            logger.warning(
                f"[TOT] Evidence truncated from {len(block)} to {max_chars} chars"
            )
        return block[:max_chars]
    except Exception as e:
        logger.warning(f"[TOT] Failed to build evidence block: {e}")
        return "(evidence unavailable)"


async def run_tot_synthesis(
    query: str,
    evidence_block: str,
    sources: List[Dict[str, Any]],
    llm_call: Callable[[str, str, Optional[int]], str],
    self_critique_fn: Callable[..., Awaitable[Any]],
    fallback_response: str,
) -> TOTResult:
    """
    Run beam-3 tree-of-thought synthesis (cost / talent / risk lens).

    Returns a TOTResult; method='tot' on success, 'fallback_linear' when
    every branch is pruned or errors.
    """
    logger.info(f"[TOT] Starting beam-3 synthesis | query={query[:120]}")

    lens_names = list(LENS_PROMPTS.keys())
    tasks = [
        _run_single_branch(
            lens=lens,
            query=query,
            evidence_block=evidence_block,
            sources=sources,
            llm_call=llm_call,
            self_critique_fn=self_critique_fn,
        )
        for lens in lens_names
    ]

    branches = await asyncio.gather(*tasks, return_exceptions=False)
    winner, runner_up = _select_winner(branches)

    if winner is None:
        logger.warning(
            "[TOT] All branches pruned or errored — falling back to linear synthesis"
        )
        return TOTResult(
            all_branches=branches,
            final_response=fallback_response,
            method="fallback_linear",
        )

    final_response = (
        _format_combined_response(winner, runner_up)
        if runner_up is not None
        else winner.thought
    )

    logger.info(
        f"[TOT] Selected '{winner.branch_id}' score={winner.score:.2f}"
        + (
            f" | runner_up='{runner_up.branch_id}' score={runner_up.score:.2f}"
            if runner_up is not None
            else ""
        )
    )

    return TOTResult(
        selected_branch=winner,
        runner_up=runner_up,
        all_branches=branches,
        final_response=final_response,
        method="tot",
    )
