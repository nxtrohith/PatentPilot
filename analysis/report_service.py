"""Report generation service for PatentPilot.

This module provides the authoritative entry-point for generating the final
patent landscape report. Like PatentAnalysisService, it extends BaseLLMService
to provide robust retry logic and error handling.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from analysis.schema import PatentReportResult
from analysis.base_service import BaseLLMService

if TYPE_CHECKING:
    from chains.report_generation import ReportGenerationInput

logger = logging.getLogger(__name__)


class ReportGenerationService(BaseLLMService):
    """Orchestrates LLM-based report generation for patent analysis results."""

    def generate(self, input_data: ReportGenerationInput) -> PatentReportResult:
        """Generate a patent landscape report with robust retries and error handling.
        
        Args:
            input_data: A fully populated ReportGenerationInput.
            
        Returns:
            A validated PatentReportResult object.
            
        Raises:
            TransientLLMError: If transient network errors persist.
            PermanentLLMError: For non-retryable API errors.
            OutputValidationError: If output parsing fails.
            PatentAnalysisError: For unexpected errors.
        """
        logger.info(
            "Generating patent report",
            extra={
                "smiles_length": len(input_data.smiles),
                "num_analyses": len(input_data.analyses),
            }
        )

        from chains.report_generation import build_structured_report_generation_chain
        
        def _call_chain() -> PatentReportResult:
            chain = build_structured_report_generation_chain(self.llm)
            return chain.invoke(input_data)  # type: ignore

        result = self._execute_with_retry(
            _call_chain,
            context_msg="report generation"
        )
        
        logger.info(
            "Report generation completed",
            extra={
                "recommendation": result.overall_recommendation.value,
            }
        )
        
        return result

__all__ = [
    "ReportGenerationService",
]
