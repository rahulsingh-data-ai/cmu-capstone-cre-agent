"""
Agent State Management for Agentic RAG.

Dataclasses for tracking agent state, execution plans, and working memory
throughout the agentic processing pipeline.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


class QueryComplexity(Enum):
    """Complexity levels for query assessment."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    RESEARCH = "research"


class StepStatus(Enum):
    """Status of an execution step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepAction(Enum):
    """Available actions for execution steps."""
    DIRECT_ANSWER = "direct_answer"
    CLARIFY = "clarify"
    RETRIEVE = "retrieve"
    ANALYZE = "analyze"
    COMPARE = "compare"
    SYNTHESIZE = "synthesize"
    GENERATE_CHART = "generate_chart"
    GENERATE_MAP = "generate_map"
    EXPORT = "export"
    REPHRASE = "rephrase"
    DIRECT_RAG = "direct_rag"
    STORM_RESEARCH = "storm_research"
    EXCEL_LOOKUP = "excel_lookup"
    EXCEL_READ = "excel_read"
    ASSET_LOOKUP = "asset_lookup"
    PDF_EXTRACT = "pdf_extract"
    IMAGE_EXTRACT = "image_extract"
    GENERATE_DIAGRAM = "generate_diagram"
    IMAGE_SEARCH = "image_search"
    MCP_CALL = "mcp_call"
    PARTNER_LOCATION = "partner_location"
    TRAVEL_TIME = "travel_time"
    MARKET_GROWTH = "market_growth"
    COMPETITIVE_INTEL = "competitive_intel"
    SELECT_COLUMNS = "select_columns"
    MERGE_TABLES = "merge_tables"
    WORKER_COST = "worker_cost"
    WORKER_TALENT = "worker_talent"
    WORKER_RISK = "worker_risk"
    WORKER_PERSONA = "worker_persona"


@dataclass
class ExecutionStep:
    """A single step in the execution plan."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    action: StepAction = StepAction.RETRIEVE
    sub_query: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action.value,
            "sub_query": self.sub_query,
            "status": self.status.value,
            "error": self.error,
            "duration_ms": self._duration_ms(),
        }

    def _duration_ms(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None


@dataclass
class WorkingMemory:
    """Working memory for storing intermediate results."""
    facts: Dict[str, Any] = field(default_factory=dict)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    step_results: Dict[str, Any] = field(default_factory=dict)

    def add_fact(self, key: str, value: Any):
        self.facts[key] = value

    def add_sources(self, new_sources: List[Dict[str, Any]]):
        """Add sources, deduplicating by source_file."""
        existing_files = {s.get("source_file") for s in self.sources}
        for source in new_sources:
            if source.get("source_file") not in existing_files:
                self.sources.append(source)
                existing_files.add(source.get("source_file"))

    def add_step_result(self, step_id: str, result: Any):
        self.step_results[step_id] = result

    def get_step_result(self, step_id: str) -> Optional[Any]:
        return self.step_results.get(step_id)

    def get_all_sources(self) -> List[Dict[str, Any]]:
        return self.sources

    def to_context_string(self) -> str:
        parts = []
        if self.facts:
            parts.append("Known Facts:")
            for key, value in self.facts.items():
                parts.append(f"- {key}: {value}")
        if self.sources:
            parts.append(f"\nSources Retrieved: {len(self.sources)} documents")
        return "\n".join(parts)


@dataclass
class Evaluation:
    """Result of evaluating a step's output."""
    meets_threshold: bool = True
    needs_refinement: bool = False
    refinement: Optional[ExecutionStep] = None
    score: float = 1.0
    reason: str = ""
    gaps: List[str] = field(default_factory=list)


@dataclass
class CritiqueResult:
    """Result of self-critique with optional corrective action."""
    score: float
    relevance: float = 0.0
    support: float = 0.0
    usefulness: float = 0.0
    reasoning: str = ""
    action: Optional[ExecutionStep] = None
    gap_query: Optional[str] = None


@dataclass
class AgentState:
    """
    Complete state of the agentic processing pipeline.

    Tracks the execution plan, current progress, working memory,
    and iteration count for the ReAct loop.
    """
    query: str = ""
    complexity: QueryComplexity = QueryComplexity.SIMPLE
    plan: List[ExecutionStep] = field(default_factory=list)
    step_index: int = 0
    iteration_count: int = 0
    max_iterations: int = 10
    memory: WorkingMemory = field(default_factory=WorkingMemory)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    final_response: Optional[str] = None
    final_confidence: float = 0.0
    error: Optional[str] = None

    def current_step(self) -> Optional[ExecutionStep]:
        if self.step_index < len(self.plan):
            return self.plan[self.step_index]
        return None

    def advance(self):
        if self.step_index < len(self.plan):
            self.plan[self.step_index].status = StepStatus.COMPLETED
            self.step_index += 1

    def add_refinement_step(self, step: ExecutionStep):
        insert_pos = self.step_index + 1
        self.plan.insert(insert_pos, step)

    def is_complete(self) -> bool:
        return self.step_index >= len(self.plan)

    def can_retry(self) -> bool:
        return self.iteration_count < self.max_iterations

    def increment_iteration(self):
        self.iteration_count += 1

    def mark_complete(self, response: str, confidence: float):
        self.completed_at = datetime.utcnow()
        self.final_response = response
        self.final_confidence = confidence

    def mark_error(self, error: str):
        self.completed_at = datetime.utcnow()
        self.error = error

    def get_duration_ms(self) -> float:
        end = self.completed_at or datetime.utcnow()
        return (end - self.started_at).total_seconds() * 1000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "complexity": self.complexity.value,
            "plan": [step.to_dict() for step in self.plan],
            "step_index": self.step_index,
            "iteration_count": self.iteration_count,
            "sources_count": len(self.memory.sources),
            "duration_ms": self.get_duration_ms(),
            "is_complete": self.is_complete(),
            "final_confidence": self.final_confidence,
            "error": self.error,
        }


@dataclass
class AgentResult:
    """Final result from the agentic orchestrator."""
    response: str
    sources: List[Dict[str, Any]]
    state: AgentState
    confidence: float
    plan_executed: List[Dict[str, Any]] = field(default_factory=list)
    trace_id: Optional[str] = None
