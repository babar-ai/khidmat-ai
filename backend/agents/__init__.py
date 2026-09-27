"""
Khidmat AI Agent State Package.

Exports the shared state schema (KhidmatState) used by the centralized
LangGraph service in services/langgraph_services.py.
"""

from agents.state import KhidmatState

__all__ = ["KhidmatState"]
