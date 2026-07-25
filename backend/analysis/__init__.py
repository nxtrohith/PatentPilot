"""Analysis package for PatentPilot.

Contains output schemas, post-processing utilities, and the service layer
for structured patent analysis results.
"""

from .schema import PatentAnalysisResult, RiskLevel, Recommendation, PatentReportResult
from .service import PatentAnalysisService, PatentBatchResult
from .report_service import ReportGenerationService
from .exceptions import (
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
    "ReportGenerationService",
    # Exceptions
    "PatentAnalysisError",
    "TransientLLMError",
    "PermanentLLMError",
    "OutputValidationError",
]
