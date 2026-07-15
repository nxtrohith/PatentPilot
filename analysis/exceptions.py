"""Custom exceptions for PatentPilot analysis and LLM operations.
"""

class PatentAnalysisError(Exception):
    """Raised when patent analysis fails after all retries are exhausted."""


class TransientLLMError(PatentAnalysisError):
    """Raised when a transient LLM error persists beyond the retry budget."""


class PermanentLLMError(PatentAnalysisError):
    """Raised for non-retryable LLM failures (e.g. bad request, auth error)."""


class OutputValidationError(PatentAnalysisError):
    """Raised when the LLM response cannot be parsed into the expected Pydantic model."""
