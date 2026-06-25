"""
Agentic Orchestrator - Fully Agentic RAG with Planning and ReAct Loops.

Transforms queries into multi-step execution plans, executes with
observation-evaluation-refinement loops, and uses self-critique
to drive iterative improvement.

Architecture:
1. Planning Phase: Assess complexity, decompose query, create plan
2. Execution Phase: ReAct loop (Execute -> Observe -> Evaluate -> Refine)
3. Synthesis Phase: Combine results, self-critique, refine if needed
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from agent_state import (
    AgentState, AgentResult, ExecutionStep, Evaluation, CritiqueResult,
    WorkingMemory, QueryComplexity, StepStatus, StepAction
)

logger = logging.getLogger(__name__)

MAX_PLAN_STEPS = 5
MAX_AGENTIC_ITERATIONS = 10
QUALITY_THRESHOLD = 0.6
MIN_SOURCES_THRESHOLD = 3


@dataclass
class AgentConfig:
    """Configuration for the agentic orchestrator."""
    enable_self_correction: bool = True
    max_iterations: int = MAX_AGENTIC_ITERATIONS
    quality_threshold: float = QUALITY_THRESHOLD


class AgenticOrchestrator:
    """
    Main orchestrator implementing the ReAct pattern with ToT synthesis.

    Flow:
        plan → execute steps → observe → evaluate → refine → synthesize
    """

    def __init__(self, tools, llm_call: Callable, config: AgentConfig = None):
        self.tools = tools
        self.llm_call = llm_call
        self.config = config or AgentConfig()

    async def process(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List] = None,
    ) -> AgentResult:
        """Main entry point: plan, execute, synthesize."""
        state = AgentState(
            query=query,
            max_iterations=self.config.max_iterations,
        )

        # Phase 1: Plan
        logger.info(f"[AGENT] Planning for query: {query[:100]}")
        state.plan = await self._create_plan(query, conversation_history)
        logger.info(f"[AGENT] Plan: {len(state.plan)} steps")

        # Phase 2: Execute (ReAct loop)
        geo = (context or {}).get("geo", "")
        while not state.is_complete() and state.can_retry():
            state.increment_iteration()
            step = state.current_step()
            if not step:
                break

            step.status = StepStatus.IN_PROGRESS
            step.started_at = datetime.utcnow()

            result = await self._execute_step(step, state, geo, conversation_history)

            step.completed_at = datetime.utcnow()
            if result.success:
                step.status = StepStatus.COMPLETED
                step.result = result.data
                if result.sources:
                    state.memory.add_sources(result.sources)
                state.memory.add_step_result(step.id, result.data)
            else:
                step.status = StepStatus.FAILED
                step.error = result.error

            # Evaluate and potentially add refinement steps
            if self.config.enable_self_correction:
                evaluation = await self._evaluate_step(step, state)
                if evaluation.needs_refinement and evaluation.refinement:
                    state.add_refinement_step(evaluation.refinement)

            state.advance()

        # Phase 3: Synthesize
        response = await self._synthesize_response(state, conversation_history)

        # Phase 3b: Tree of Thought (if enabled and complex enough)
        try:
            from config import ENABLE_TOT_SYNTHESIS
        except ImportError:
            ENABLE_TOT_SYNTHESIS = False

        if ENABLE_TOT_SYNTHESIS:
            try:
                from tot_synthesizer import (
                    build_evidence_block,
                    run_tot_synthesis,
                    should_use_tot,
                )
                if should_use_tot(state):
                    logger.info(
                        "[AGENT] Complex multi-pillar query — invoking ToT synthesis"
                    )
                    tot_result = await run_tot_synthesis(
                        query=state.query,
                        evidence_block=build_evidence_block(state),
                        sources=state.memory.get_all_sources(),
                        llm_call=self.llm_call,
                        self_critique_fn=self._self_critique,
                        fallback_response=response,
                    )
                    if tot_result.method == "tot" and tot_result.selected_branch:
                        response = tot_result.final_response
                        logger.info(
                            f"[AGENT] ToT selected '{tot_result.selected_branch.branch_id}'"
                            f" score={tot_result.selected_branch.score:.2f}"
                        )
            except Exception as e:
                logger.warning(f"[AGENT] ToT synthesis failed, using linear: {e}")

        # Finalize
        confidence = await self._compute_confidence(state)
        state.mark_complete(response, confidence)

        return AgentResult(
            response=response,
            sources=state.memory.get_all_sources(),
            state=state,
            confidence=confidence,
            plan_executed=[s.to_dict() for s in state.plan],
        )

    async def _create_plan(self, query: str, conversation_history=None) -> List[ExecutionStep]:
        """Decompose query into execution steps via LLM."""
        # In production, this calls the LLM with a planning prompt
        # Simplified for demonstration
        return [ExecutionStep(action=StepAction.RETRIEVE, sub_query=query)]

    async def _execute_step(self, step, state, geo, conversation_history):
        """Execute a single step using the appropriate tool."""
        # In production, this dispatches to vector_search, SQL, chart gen, etc.
        raise NotImplementedError("Override in production with tool dispatch")

    async def _evaluate_step(self, step, state) -> Evaluation:
        """Evaluate step quality and determine if refinement is needed."""
        if step.status == StepStatus.FAILED:
            return Evaluation(
                meets_threshold=False,
                needs_refinement=True,
                refinement=ExecutionStep(
                    action=StepAction.REPHRASE,
                    sub_query=f"Rephrase: {step.sub_query}",
                ),
            )
        return Evaluation(meets_threshold=True)

    async def _synthesize_response(self, state, conversation_history=None) -> str:
        """Synthesize final response from accumulated evidence."""
        # In production, this builds a synthesis prompt with all sources
        return state.final_response or "Synthesis complete."

    async def _self_critique(self, query, response, sources, llm_call) -> CritiqueResult:
        """Score a response for relevance, support, and usefulness."""
        # In production, uses LLM to score the response
        return CritiqueResult(score=0.8, relevance=0.8, support=0.8, usefulness=0.8)

    async def _compute_confidence(self, state) -> float:
        """Compute overall confidence from source count and step success."""
        total = len(state.plan)
        completed = sum(1 for s in state.plan if s.status == StepStatus.COMPLETED)
        source_factor = min(len(state.memory.sources) / MIN_SOURCES_THRESHOLD, 1.0)
        step_factor = completed / max(total, 1)
        return round((source_factor * 0.6 + step_factor * 0.4), 2)
