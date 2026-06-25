"""
Logging Setup - Color-coded structured logging for agent stages.

Provides visual distinction between different phases of agent execution:
- PLANNING (yellow): routing, thinking, decomposition
- FETCH (cyan): vector search, RAG queries
- EXECUTION (green): workers, tools, MCP calls
- SYNTHESIS (magenta): ToT, CoT, STORM, subagents
- QUALITY (dim magenta): critique, errors, confidence
- DELIVERY (blue): streaming responses
- INFRA (grey): network, caching, router
"""

import logging
import sys
from datetime import datetime

STAGE_PALETTE = {
    'PLANNING':  '\033[93;1m',   # bright yellow bold
    'FETCH':     '\033[36m',     # cyan
    'EXECUTION': '\033[92;1m',   # bright green bold
    'SYNTHESIS': '\033[95;1m',   # bright magenta bold
    'QUALITY':   '\033[35m',     # plain magenta
    'DELIVERY':  '\033[94;1m',   # bright blue bold
    'INFRA':     '\033[2;90m',   # dim grey
}

TAG_STAGES = {
    # Planning stage
    'ROUTING':      'PLANNING',
    'THINKING':     'PLANNING',
    'PLANNING':     'PLANNING',
    'COT':          'PLANNING',
    'PLAN':         'PLANNING',
    'COMPLEXITY':   'PLANNING',
    'DECOMPOSE':    'PLANNING',

    # Fetch stage
    'VECTOR_SEARCH':'FETCH',
    'RAG_QUERY':    'FETCH',
    'RAG':          'FETCH',
    'STANDARD_RAG': 'FETCH',
    'HYBRID':       'FETCH',
    'PDF_CONTEXT':  'FETCH',
    'RETRIEVE':     'FETCH',

    # Execution stage
    'WORKER':       'EXECUTION',
    'WORKER_COST':  'EXECUTION',
    'WORKER_TALENT':'EXECUTION',
    'WORKER_RISK':  'EXECUTION',
    'TOOL':         'EXECUTION',
    'SQL':          'EXECUTION',
    'CHART':        'EXECUTION',
    'MAP':          'EXECUTION',
    'MCP':          'EXECUTION',
    'MCP_CALL':     'EXECUTION',
    'EXCEL':        'EXECUTION',

    # Synthesis stage
    'TOT':          'SYNTHESIS',
    'ToT':          'SYNTHESIS',
    'SYNTHESIS':    'SYNTHESIS',
    'SUBAGENT':     'SYNTHESIS',
    'STORM':        'SYNTHESIS',
    'RLM':          'SYNTHESIS',
    'LANGGRAPH':    'SYNTHESIS',

    # Quality stage
    'CRITIQUE':     'QUALITY',
    'SELF_CRITIQUE':'QUALITY',
    'CONFIDENCE':   'QUALITY',
    'EXCEPTION':    'QUALITY',
    'ERROR':        'QUALITY',

    # Delivery stage
    'STREAM':       'DELIVERY',
    'SSE':          'DELIVERY',
    'REQUEST':      'DELIVERY',
    'RESPONSE':     'DELIVERY',

    # Infrastructure
    'CACHE':        'INFRA',
    'NETWORK':      'INFRA',
    'ROUTER':       'INFRA',
    'STARTUP':      'INFRA',
}

RESET = '\033[0m'


class ColoredAgentFormatter(logging.Formatter):
    """Formatter that color-codes log lines based on agent stage tags."""

    def format(self, record):
        msg = record.getMessage()
        color = None

        # Detect [TAG] pattern in the message
        if '[' in msg:
            for tag, stage in TAG_STAGES.items():
                if f'[{tag}]' in msg:
                    color = STAGE_PALETTE.get(stage)
                    break

        if color:
            return f"{color}{self._format_line(record)}{RESET}"
        return self._format_line(record)

    def _format_line(self, record):
        ts = datetime.utcnow().strftime('%H:%M:%S.%f')[:-3]
        return f"{ts} | {record.levelname:<7} | {record.getMessage()}"


def setup_logging(level=logging.INFO):
    """Configure logging with color-coded agent stages."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColoredAgentFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return root
