"""LLM package for PatentPilot.

This package provides the provider-agnostic LLM factory and all prompt
templates used across the application.

Supported providers: ``nvidia`` (default, GLM-5.2) and ``groq`` (fallback).
The active provider is controlled by the ``LLM_PROVIDER`` environment variable.
"""

from .provider import get_llm
from .prompts import (
    PATENT_ANALYSIS_PROMPT,
    REPORT_GENERATION_PROMPT,
    build_patent_analysis_messages,
    build_report_messages,
)

__all__ = [
    "get_llm",
    "PATENT_ANALYSIS_PROMPT",
    "REPORT_GENERATION_PROMPT",
    "build_patent_analysis_messages",
    "build_report_messages",
]
