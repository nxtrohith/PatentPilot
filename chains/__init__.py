"""Chains package for PatentPilot.

Each module in this package exposes a reusable LangChain LCEL chain and a
higher-level convenience function for a specific analysis workflow.

Available chains
----------------
patent_analysis
    Connects the patent-analysis prompt with the Groq LLM.
    - ``build_patent_analysis_chain`` → raw ``AIMessage``
    - ``build_structured_patent_analysis_chain`` → :class:`~analysis.schema.PatentAnalysisResult`
"""

from .patent_analysis import (
    PatentAnalysisInput,
    build_patent_analysis_chain,
    run_patent_analysis,
    build_structured_patent_analysis_chain,
    run_structured_patent_analysis,
)

__all__ = [
    "PatentAnalysisInput",
    "build_patent_analysis_chain",
    "run_patent_analysis",
    "build_structured_patent_analysis_chain",
    "run_structured_patent_analysis",
]
