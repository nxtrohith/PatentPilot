"""Analysis package for PatentPilot.

Contains output schemas, post-processing utilities, and the service layer
for structured patent analysis results.
"""

from .schema import PatentAnalysisResult, RiskLevel, Recommendation, PatentReportResult
from .service import (
    PatentAnalysisService,
    PatentBatchResult,
    PatentAnalysisError,
    TransientLLMError,
    PermanentLLMError,
    OutputValidationError,
)

__all__ = [
    # Schema
    "PatentAnalysisResult",
    "RiskLevel",
    "Recommendation",
    "PatentReportResult",
    # Service
    "PatentAnalysisService",
    "PatentBatchResult",
    # Exceptions
    "PatentAnalysisError",
    "TransientLLMError",
    "PermanentLLMError",
    "OutputValidationError",
]
