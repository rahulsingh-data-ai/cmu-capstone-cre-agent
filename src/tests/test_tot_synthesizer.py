"""Tests for the Tree-of-Thought synthesizer."""

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from tot_synthesizer import (
    PRUNE_THRESHOLD,
    TIE_THRESHOLD,
    TOTBranch,
    _format_combined_response,
    _select_winner,
    run_tot_synthesis,
)


def test_thresholds_match_design_spec():
    assert PRUNE_THRESHOLD == 0.5
    assert TIE_THRESHOLD == 0.1


def test_select_winner_picks_highest_score():
    branches = [
        TOTBranch(branch_id="cost", lens="cost", score=0.85),
        TOTBranch(branch_id="talent", lens="talent", score=0.60),
        TOTBranch(branch_id="risk", lens="risk", score=0.70),
    ]
    winner, runner_up = _select_winner(branches)
    assert winner.branch_id == "cost"
    assert runner_up is None  # 0.85 - 0.70 = 0.15 > TIE_THRESHOLD


def test_select_winner_returns_runner_up_when_tied():
    branches = [
        TOTBranch(branch_id="cost", lens="cost", score=0.85),
        TOTBranch(branch_id="talent", lens="talent", score=0.80),
        TOTBranch(branch_id="risk", lens="risk", score=0.50),
    ]
    winner, runner_up = _select_winner(branches)
    assert winner.branch_id == "cost"
    assert runner_up.branch_id == "talent"


def test_select_winner_skips_pruned_branches():
    branches = [
        TOTBranch(branch_id="cost", lens="cost", score=0.40, is_pruned=True),
        TOTBranch(branch_id="talent", lens="talent", score=0.60),
        TOTBranch(branch_id="risk", lens="risk", score=0.70),
    ]
    winner, _ = _select_winner(branches)
    assert winner.branch_id == "risk"


def test_select_winner_returns_none_when_all_pruned():
    branches = [
        TOTBranch(branch_id="cost", lens="cost", score=0.30, is_pruned=True),
        TOTBranch(branch_id="talent", lens="talent", score=0.20, is_pruned=True),
    ]
    winner, runner_up = _select_winner(branches)
    assert winner is None
    assert runner_up is None


def test_format_combined_response_includes_both_branches():
    winner = TOTBranch(branch_id="cost", lens="cost", thought="Cost-led recommendation.")
    runner_up = TOTBranch(branch_id="risk", lens="risk", thought="Risk-led alternative.")
    out = _format_combined_response(winner, runner_up)
    assert "Cost-led recommendation" in out
    assert "Risk-led alternative" in out
    assert "primary lens: cost" in out
    assert "Alternative view" in out


def _make_critique_result(score: float):
    """Build a minimal CritiqueResult-like object."""
    class _CR:
        def __init__(self, s):
            self.score = s
            self.relevance = s
            self.support = s
            self.usefulness = s
            self.reasoning = "test"
    return _CR(score)


@pytest.mark.asyncio
async def test_run_tot_synthesis_falls_back_when_all_pruned():
    """All branches scoring below PRUNE_THRESHOLD → return fallback response."""

    def fake_llm(system, user, max_tokens):
        return "synthesis text"

    async def fake_critique(query, response, sources, llm_call):
        return _make_critique_result(0.30)

    result = await run_tot_synthesis(
        query="test query",
        evidence_block="some evidence",
        sources=[],
        llm_call=fake_llm,
        self_critique_fn=fake_critique,
        fallback_response="LINEAR FALLBACK",
    )

    assert result.method == "fallback_linear"
    assert result.final_response == "LINEAR FALLBACK"
    assert result.selected_branch is None
    assert len(result.all_branches) == 3
    assert all(b.is_pruned for b in result.all_branches)


@pytest.mark.asyncio
async def test_run_tot_synthesis_selects_highest_scoring_branch():
    """When branches differ in score, ToT picks the highest above prune threshold."""

    def fake_llm(system, user, max_tokens):
        if "COST" in system:
            return "COST_THOUGHT: cost analysis."
        if "TALENT" in system:
            return "TALENT_THOUGHT: talent analysis."
        if "RISK" in system:
            return "RISK_THOUGHT: risk analysis."
        return "GENERIC"

    async def fake_critique(query, response, sources, llm_call):
        if "COST_THOUGHT" in response:
            return _make_critique_result(0.90)
        if "TALENT_THOUGHT" in response:
            return _make_critique_result(0.60)
        if "RISK_THOUGHT" in response:
            return _make_critique_result(0.65)
        return _make_critique_result(0.40)

    result = await run_tot_synthesis(
        query="compare markets",
        evidence_block="evidence",
        sources=[],
        llm_call=fake_llm,
        self_critique_fn=fake_critique,
        fallback_response="should not be used",
    )

    assert result.method == "tot"
    assert result.selected_branch.branch_id == "cost"
    assert result.selected_branch.score == 0.90
    assert "COST_THOUGHT" in result.final_response
    assert result.runner_up is None  # 0.90 - 0.65 = 0.25 > TIE_THRESHOLD


@pytest.mark.asyncio
async def test_run_tot_synthesis_handles_branch_errors_gracefully():
    """If one branch raises during generation, others still complete."""

    def fake_llm(system, user, max_tokens):
        if "TALENT" in system:
            raise RuntimeError("simulated LLM failure")
        return "ok response"

    async def fake_critique(query, response, sources, llm_call):
        return _make_critique_result(0.80)

    result = await run_tot_synthesis(
        query="q",
        evidence_block="e",
        sources=[],
        llm_call=fake_llm,
        self_critique_fn=fake_critique,
        fallback_response="fallback",
    )

    assert result.method == "tot"
    talent_branch = next(b for b in result.all_branches if b.branch_id == "talent")
    assert talent_branch.is_pruned
    assert talent_branch.error is not None
    assert result.selected_branch.branch_id in ("cost", "risk")
