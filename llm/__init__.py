"""LLM package for PatentPilot.

This package handles interactions with Language Models, specifically Groq.
"""

from .provider import get_llm, DEFAULT_MODEL

__all__ = ["get_llm", "DEFAULT_MODEL"]
