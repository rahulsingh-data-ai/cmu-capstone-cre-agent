"""Integration tests for ToT gating inside AgenticOrchestrator."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))

from agent_state import ExecutionStep, StepAction
from agent_tools import AgentTools, ToolResult
from agentic_orchestrator import AgentConfig, AgenticOrchestrator
from tot_synthesizer import TOTBranch, TOTResult
import agentic_orchestrator as orch_mod
import config as app_config
import tot_synthesizer as tot_mod


def _make_tools():
    return AgentTools(
        vector_search_fn=MagicMock(return_value=([], [])),
        llm_call_fn=MagicMock(return_value="tools llm"),
        excel_registry_fn=MagicMock(return_value=[]),
    )


def _worker_output(section: str):
    return {
        "worker_output": {
            "section": section,
            "claims": [{"text": f"{section} claim", "citations": ["doc.pdf:1"]}],
            "metrics": [],
            "risks": [],
            "missing_data": [],
        }
    }


async def _fake_execute_step(self, step, state, geo, conversation_history):
    if step.action == StepAction.WORKER_COST:
        return ToolResult(
            success=True,
            data=_worker_output("Cost"),
            sources=[{"source_file": "cost.pdf", "text": "cost evidence", "page_number": 1}],
        )
    if step.action == StepAction.WORKER_TALENT:
        return ToolResult(
            success=True,
            data=_worker_output("Talent"),
            sources=[{"source_file": "talent.pdf", "text": "talent evidence", "page_number": 2}],
        )
    if step.action == StepAction.WORKER_RISK:
        return ToolResult(
            success=True,
            data=_worker_output("Risk"),
            sources=[{"source_file": "risk.pdf", "text": "risk evidence", "page_number": 3}],
        )
    return ToolResult(success=True, data={"response": "ok"})


def _make_orchestrator(monkeypatch):
    tools = _make_tools()
    llm_call = MagicMock(return_value="llm output")
    cfg = AgentConfig(enable_self_correction=False)
    orch = AgenticOrchestrator(tools=tools, llm_call=llm_call, config=cfg)
    monkeypatch.setattr(AgenticOrchestrator, "_execute_step", _fake_execute_step)

    async def _linear_synth(self, state, conversation_history=None):
        return "LINEAR_SYNTH"

    monkeypatch.setattr(AgenticOrchestrator, "_synthesize_response", _linear_synth)
    return orch


def _patch_plan(monkeypatch, actions):
    async def _fake_plan(self, query, conversation_history=None):
        return [
            ExecutionStep(id=f"step{i}", action=action, sub_query=f"{action.value}")
            for i, action in enumerate(actions, start=1)
        ]

    monkeypatch.setattr(AgenticOrchestrator, "_create_plan", _fake_plan)


@pytest.mark.asyncio
async def test_tot_not_called_when_flag_disabled(monkeypatch):
    _patch_plan(
        monkeypatch,
        [StepAction.WORKER_COST, StepAction.WORKER_TALENT, StepAction.WORKER_RISK],
    )
    monkeypatch.setattr(app_config, "ENABLE_TOT_SYNTHESIS", False)
    tot_mock = AsyncMock(
        return_value=TOTResult(
            selected_branch=TOTBranch(branch_id="cost", lens="cost", thought="tot"),
            final_response="TOT_SYNTH",
            method="tot",
        )
    )
    monkeypatch.setattr(tot_mod, "run_tot_synthesis", tot_mock)

    orch = _make_orchestrator(monkeypatch)
    result = await orch.process("compare markets", context={"geo": "US"})

    assert result.response == "LINEAR_SYNTH"
    tot_mock.assert_not_called()


@pytest.mark.asyncio
async def test_tot_not_called_below_worker_threshold(monkeypatch):
    _patch_plan(monkeypatch, [StepAction.WORKER_COST, StepAction.WORKER_TALENT])
    monkeypatch.setattr(app_config, "ENABLE_TOT_SYNTHESIS", True)
    tot_mock = AsyncMock(
        return_value=TOTResult(
            selected_branch=TOTBranch(branch_id="cost", lens="cost", thought="tot"),
            final_response="TOT_SYNTH",
            method="tot",
        )
    )
    monkeypatch.setattr(tot_mod, "run_tot_synthesis", tot_mock)

    orch = _make_orchestrator(monkeypatch)
    result = await orch.process("compare markets", context={"geo": "US"})

    assert result.response == "LINEAR_SYNTH"
    tot_mock.assert_not_called()


@pytest.mark.asyncio
async def test_tot_called_when_enabled_and_threshold_met(monkeypatch):
    _patch_plan(
        monkeypatch,
        [StepAction.WORKER_COST, StepAction.WORKER_TALENT, StepAction.WORKER_RISK],
    )
    monkeypatch.setattr(app_config, "ENABLE_TOT_SYNTHESIS", True)
    tot_mock = AsyncMock(
        return_value=TOTResult(
            selected_branch=TOTBranch(
                branch_id="risk",
                lens="risk",
                thought="Risk-led recommendation",
                score=0.82,
            ),
            final_response="TOT_SYNTH",
            method="tot",
        )
    )
    monkeypatch.setattr(tot_mod, "run_tot_synthesis", tot_mock)

    orch = _make_orchestrator(monkeypatch)
    result = await orch.process("compare markets", context={"geo": "US"})

    assert result.response == "TOT_SYNTH"
    tot_mock.assert_called_once()
