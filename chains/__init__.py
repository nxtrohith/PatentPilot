"""Chains package for PatentPilot.

Each module in this package exposes a reusable LangChain LCEL chain and a
higher-level convenience function for a specific analysis workflow.

Available chains
----------------
patent_analysis
    Connects the patent-analysis prompt with the Groq LLM.
    - ``build_patent_analysis_chain`` → raw ``AIMessage``
    - ``build_structured_patent_analysis_chain`` → :class:`~analysis.schema.PatentAnalysisResult`
report_generation
    Connects the report-generation prompt with the LLM.
    - ``build_structured_report_generation_chain`` → :class:`~analysis.schema.PatentReportResult`
"""

from .patent_analysis import (
    PatentAnalysisInput,
    build_patent_analysis_chain,
    run_patent_analysis,
    build_structured_patent_analysis_chain,
    run_structured_patent_analysis,
)
from .report_generation import (
    ReportGenerationInput,
    build_structured_report_generation_chain,
    run_structured_report_generation,
)

__all__ = [
    "PatentAnalysisInput",
    "build_patent_analysis_chain",
    "run_patent_analysis",
    "build_structured_patent_analysis_chain",
    "run_structured_patent_analysis",
    "ReportGenerationInput",
    "build_structured_report_generation_chain",
    "run_structured_report_generation",
]
