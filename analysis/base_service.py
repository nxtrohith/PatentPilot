"""Base service for executing LLM chains with robust retries and error handling."""

from __future__ import annotations

import logging
from typing import Any, Callable, TypeVar

from groq import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    RateLimitError,
)
from pydantic import ValidationError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from langchain_core.language_models.chat_models import BaseChatModel

from .exceptions import (
    OutputValidationError,
    PatentAnalysisError,
    PermanentLLMError,
    TransientLLMError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

#: Maximum number of attempts before giving up (1 initial + N-1 retries).
_MAX_ATTEMPTS: int = 4

#: Minimum wait between retries in seconds.
_WAIT_MIN_SECONDS: float = 2.0

#: Maximum wait between retries in seconds.
_WAIT_MAX_SECONDS: float = 30.0

#: Groq error types treated as transient (safe to retry).
_TRANSIENT_EXCEPTIONS = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
)


class BaseLLMService:
    """Base class for robust LLM execution.
    
    Provides dependency injection for the LLM and handles standard error wrapping
    and exponential back-off retries for transient failures.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        max_attempts: int = _MAX_ATTEMPTS,
    ) -> None:
        """
        Args:
            llm: The configured LangChain chat model to use for execution.
            max_attempts: Maximum number of attempts for transient errors.
        """
        self.llm = llm
        self._max_attempts = max_attempts

    def _execute_with_retry(
        self,
        func: Callable[[], T],
        context_msg: str = "LLM execution",
    ) -> T:
        """Execute a callable with automatic retry and standard error mapping.
        
        Args:
            func: A zero-argument callable that runs the chain.
            context_msg: A string describing the operation for error logs.
            
        Returns:
            The result of `func()`.
            
        Raises:
            TransientLLMError: If transient errors persist beyond the retry budget.
            PermanentLLMError: For non-retryable API errors.
            OutputValidationError: If Pydantic validation fails.
            PatentAnalysisError: For other unexpected failures.
        """
        @retry(
            retry=retry_if_exception_type(_TRANSIENT_EXCEPTIONS),
            stop=stop_after_attempt(self._max_attempts),
            wait=wait_exponential(
                multiplier=1,
                min=_WAIT_MIN_SECONDS,
                max=_WAIT_MAX_SECONDS,
            ),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def _call_with_retry() -> T:
            return func()

        try:
            return _call_with_retry()
        except _TRANSIENT_EXCEPTIONS as exc:
            msg = f"Transient LLM error persisted after {self._max_attempts} attempts during {context_msg}: {exc}"
            logger.error(msg, exc_info=True)
            wrapped = TransientLLMError(msg)
            wrapped.__cause__ = exc
            raise wrapped from exc
        except APIStatusError as exc:
            msg = f"Non-retryable LLM API error (HTTP {exc.status_code}) during {context_msg}: {exc.message}"
            logger.error(msg, exc_info=True)
            wrapped = PermanentLLMError(msg)
            wrapped.__cause__ = exc
            raise wrapped from exc
        except ValidationError as exc:
            msg = f"LLM output failed Pydantic validation during {context_msg}: {exc}"
            logger.error(msg, exc_info=True)
            wrapped = OutputValidationError(msg)
            wrapped.__cause__ = exc
            raise wrapped from exc
        except PatentAnalysisError:
            # Already wrapped, re-raise directly
            raise
        except Exception as exc:
            msg = f"Unexpected error during {context_msg}: {exc}"
            logger.error(msg, exc_info=True)
            wrapped = PatentAnalysisError(msg)
            wrapped.__cause__ = exc
            raise wrapped from exc
