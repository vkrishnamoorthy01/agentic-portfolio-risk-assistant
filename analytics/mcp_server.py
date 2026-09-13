"""MCP server exposing the same portfolio risk tools as service.py's HTTP API.

Same underlying logic (service.py, retrieval.py), a different transport.
Compare this file against how these tools had to be wired into Make in
V1-V4: there, each tool needed a hand-typed URL, HTTP method, and a
hand-written tool-description string inside Make's UI before an agent
could use it. Here, an MCP host discovers the tool's name, arguments, and
purpose directly from this file's decorators/type hints/docstrings, no
separate description to keep in sync, no URL to copy-paste.

Run directly for a quick manual check: `python mcp_server.py`
Run as an MCP server (stdio transport, the default): registered via
.mcp.json and started automatically by an MCP host such as Claude Code.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.mcpserver import MCPServer

from retrieval import retrieve
from service import get_analytics

mcp = MCPServer("portfolio-risk-tools")


@mcp.tool()
def get_portfolio_analytics() -> dict:
    """Get live portfolio risk analytics for the 16-stock NSE equal-weighted
    portfolio: 1-day return, 20-day annualized volatility, 99% one-day
    historical VaR, drawdown from peak, largest position (concentration),
    and top contributors/detractors. Use this whenever a question needs
    current numbers, not policy interpretation.
    """
    return get_analytics()


@mcp.tool()
def get_risk_policy_sections(query: str, top_k: int = 2) -> dict:
    """Retrieve the risk policy sections most relevant to a natural-language
    query, e.g. position concentration limits, volatility thresholds, VaR
    limits, or drawdown escalation rules. Use this whenever a question needs
    the firm's policy limits, not live portfolio numbers.
    """
    return {"query": query, "results": retrieve(query, top_k=top_k)}


if __name__ == "__main__":
    mcp.run()
