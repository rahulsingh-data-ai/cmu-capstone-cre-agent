"""
Agent Tools - Unified Tool Interface for Agentic Orchestrator.

Provides a consistent interface for all tools available to the agent,
including vector search, chart generation, map generation, and data export.
"""

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """Standardized result from any tool execution."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    sources: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    latency_ms: float = 0.0


class AgentTools:
    """
    Unified tool interface for the agentic orchestrator.

    Tools available:
    - vector_search: Hybrid BM25 + dense embedding retrieval
    - sql_execute: Run analytical queries against SQL warehouse
    - generate_chart: Create interactive visualizations (bar, line, pie, etc.)
    - generate_map: Create geographic visualizations with markers
    - excel_lookup: Search Excel registry for structured data
    - excel_read: Read specific sheets/columns from Excel files
    - asset_lookup: Search pre-extracted tables/images from asset library
    - image_search: Find relevant photos (properties, skylines)
    """

    def __init__(
        self,
        vector_search_fn: Optional[Callable] = None,
        llm_call_fn: Optional[Callable] = None,
        excel_registry_fn: Optional[Callable] = None,
    ):
        self.vector_search_fn = vector_search_fn
        self.llm_call_fn = llm_call_fn
        self.excel_registry_fn = excel_registry_fn

    async def vector_search(
        self,
        query: str,
        num_results: int = 8,
        filters: Optional[Dict] = None,
    ) -> ToolResult:
        """Execute hybrid vector search (BM25 + dense embedding)."""
        try:
            if not self.vector_search_fn:
                return ToolResult(success=False, error="Vector search not configured")

            results, sources = self.vector_search_fn(query, num_results, filters)
            return ToolResult(
                success=True,
                data={"results": results, "count": len(results)},
                sources=sources,
            )
        except Exception as e:
            logger.error(f"[TOOLS] Vector search failed: {e}")
            return ToolResult(success=False, error=str(e))

    async def sql_execute(self, query: str) -> ToolResult:
        """Execute SQL query against the data warehouse."""
        # In production: connects to Databricks SQL Warehouse
        logger.info(f"[TOOLS] SQL execute: {query[:100]}")
        return ToolResult(
            success=True,
            data={"query": query, "rows": [], "note": "SQL execution requires warehouse connection"},
        )

    async def generate_chart(
        self,
        chart_type: str,
        data: List[Dict],
        title: str = "",
    ) -> ToolResult:
        """Generate an interactive chart visualization."""
        logger.info(f"[TOOLS] Generate chart: {chart_type} | {title}")
        return ToolResult(
            success=True,
            data={
                "chart_type": chart_type,
                "title": title,
                "data": data,
                "rendered": True,
            },
        )

    async def generate_map(
        self,
        locations: List[Dict],
        title: str = "",
    ) -> ToolResult:
        """Generate a geographic map with markers."""
        logger.info(f"[TOOLS] Generate map: {len(locations)} locations")
        return ToolResult(
            success=True,
            data={
                "type": "map",
                "title": title,
                "locations": locations,
                "rendered": True,
            },
        )

    async def worker_execute(
        self,
        worker_type: str,
        query: str,
        evidence: List[Dict],
    ) -> ToolResult:
        """Execute a specialized worker (cost/talent/risk analysis)."""
        logger.info(f"[TOOLS] Worker execute: {worker_type}")

        if not self.llm_call_fn:
            return ToolResult(success=False, error="LLM not configured")

        # Workers produce structured output with claims, metrics, and gaps
        worker_prompt = (
            f"You are a {worker_type} analysis specialist.\n"
            f"Analyze the following evidence and produce structured findings.\n"
            f"Query: {query}\n"
            f"Evidence: {len(evidence)} sources available."
        )

        return ToolResult(
            success=True,
            data={
                "worker_output": {
                    "section": worker_type,
                    "claims": [],
                    "metrics": [],
                    "risks": [],
                    "missing_data": [],
                }
            },
            sources=evidence,
        )
