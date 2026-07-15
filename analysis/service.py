"""Patent analysis service for PatentPilot.

This module is the single, authoritative entry-point for running LLM-powered
patent analysis on one or more patent documents.  It is intentionally decoupled
from:

- **UI / presentation** — the service returns typed Pydantic objects; callers
  decide how to display them.
- **Retrieval** — the service accepts pre-fetched
  :class:`~chains.patent_analysis.PatentAnalysisInput` objects; callers decide
  how to source patents.

Responsibilities
----------------
1. Receive one patent **or** a list of patents.
2. Invoke the structured analysis chain (per patent).
3. Return validated :class:`~analysis.schema.PatentAnalysisResult` objects.
4. Catch and classify LLM failures.
5. Retry transient errors with exponential back-off (via *tenacity*).
6. Log every failure with structured context.
7. For batch calls: preserve original ordering, continue on individual failures,
   and return both successes and failures together.

Usage — single patent::

    from dotenv import load_dotenv
    load_dotenv()

    from chains.patent_analysis import PatentAnalysisInput
    from analysis.service import PatentAnalysisService

    service = PatentAnalysisService()
    result = service.analyse(
        PatentAnalysisInput(
            smiles="CC(=O)Oc1ccccc1C(=O)O",
            patent_title="Novel salicylate derivatives ...",
            patent_abstract="The present invention relates to ...",
            publication_date="2022-03-10",
            assignee="Pharma Corp Ltd",
            disease="Pain",
            target="COX-2",
        )
    )
    print(result.risk_level)

Usage — batch::

    batch = service.analyse_batch([patent_a, patent_b, patent_c])
    for item in batch:
        if item.success:
            print(item.result.risk_level)
        else:
            print(item.error)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

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

from analysis.schema import PatentAnalysisResult

# Imported only for type-checking to avoid a circular import at runtime:
# chains.patent_analysis → analysis.schema → analysis.__init__ → analysis.service
# → chains.patent_analysis (cycle).  The real import happens lazily inside
# _invoke_with_retry where it is always safe.
if TYPE_CHECKING:
    from chains.patent_analysis import PatentAnalysisInput

# ---------------------------------------------------------------------------
# Module logger
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry policy constants
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class PatentAnalysisError(Exception):
    """Raised when patent analysis fails after all retries are exhausted."""


class TransientLLMError(PatentAnalysisError):
    """Raised when a transient LLM error persists beyond the retry budget."""


class PermanentLLMError(PatentAnalysisError):
    """Raised for non-retryable LLM failures (e.g. bad request, auth error)."""


class OutputValidationError(PatentAnalysisError):
    """Raised when the LLM response cannot be parsed into PatentAnalysisResult."""


# ---------------------------------------------------------------------------
# Batch result container
# ---------------------------------------------------------------------------


@dataclass
class PatentBatchResult:
    """Outcome for one patent within a batch analysis run.

    Attributes:
        index: Zero-based position of this patent in the original input list.
            Preserved regardless of processing order so callers can correlate
            results back to their source data.
        patent_title: Title of the patent, copied from the input for
            convenience (useful when logging or displaying results without
            access to the original input list).
        result: The validated :class:`~analysis.schema.PatentAnalysisResult`
            if analysis succeeded; ``None`` otherwise.
        error: The exception raised if analysis failed; ``None`` on success.

    Properties:
        success: ``True`` when ``result`` is populated.
        failure: ``True`` when ``error`` is populated.
    """

    index: int
    patent_title: str
    result: Optional[PatentAnalysisResult] = field(default=None)
    error: Optional[Exception] = field(default=None)

    @property
    def success(self) -> bool:
        """Return ``True`` if this patent was analysed successfully."""
        return self.result is not None

    @property
    def failure(self) -> bool:
        """Return ``True`` if this patent's analysis raised an exception."""
        return self.error is not None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class PatentAnalysisService:
    """Orchestrates LLM-based analysis for one or many patent documents.

    The service is stateless between calls; a single instance can be shared
    across threads or requests.  LLM configuration is fixed at construction
    time and forwarded to the provider on every call.

    Args:
        model_name: Optional model identifier override.  When ``None`` the
            value configured in :func:`~llm.provider.get_llm` is used (env
            var ``NVIDIA_MODEL`` / ``GROQ_MODEL`` or the hard-coded default).
        temperature: Sampling temperature forwarded to the LLM. Defaults to
            ``1.0`` to match GLM-5.2's recommended setting.
        max_attempts: Total number of attempts for transient errors (including
            the initial attempt). Defaults to :data:`_MAX_ATTEMPTS`.
        top_p: Nucleus-sampling probability mass (NVIDIA/GLM only).
            Defaults to ``1`` (consider all tokens).
        max_tokens: Maximum completion tokens (NVIDIA/GLM only).
            Defaults to ``16384``.
        seed: Fixed random seed for reproducible outputs (NVIDIA/GLM only).
            Defaults to ``42``.

    Example::

        service = PatentAnalysisService()  # uses GLM-5.2 defaults

        # Single patent
        result = service.analyse(patent_input)

        # Batch of patents
        batch = service.analyse_batch([p1, p2, p3])
        successes = [b for b in batch if b.success]
        failures  = [b for b in batch if b.failure]
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: float = 1.0,
        max_attempts: int = _MAX_ATTEMPTS,
        top_p: Optional[float] = 1.0,
        max_tokens: Optional[int] = 16384,
        seed: Optional[int] = 42,
    ) -> None:
        self._model_name   = model_name
        self._temperature  = temperature
        self._max_attempts = max_attempts
        self._top_p        = top_p
        self._max_tokens   = max_tokens
        self._seed         = seed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyse(self, patent: PatentAnalysisInput) -> PatentAnalysisResult:
        """Analyse a single patent and return a validated result.

        The method delegates to the structured analysis chain and wraps all
        known failure modes with descriptive exceptions and structured logging.

        Args:
            patent: A fully populated :class:`~chains.patent_analysis.PatentAnalysisInput`.

        Returns:
            A validated :class:`~analysis.schema.PatentAnalysisResult` Pydantic
            object.

        Raises:
            TransientLLMError: If transient network/rate-limit errors persist
                beyond the retry budget.
            PermanentLLMError: For non-retryable API errors (e.g. auth failure,
                invalid request).
            OutputValidationError: If the model's structured output fails Pydantic
                validation.
            PatentAnalysisError: For any other unexpected failure.
        """
        outcome = self._analyse_one(patent, index=0)
        if outcome.failure:
            raise outcome.error  # type: ignore[misc]
        return outcome.result  # type: ignore[return-value]

    def analyse_batch(
        self,
        patents: list[PatentAnalysisInput],
    ) -> list[PatentBatchResult]:
        """Analyse a list of patents, continuing past individual failures.

        Each patent is processed via :meth:`analyse`.  If a patent raises any
        exception, the error is captured in the corresponding
        :class:`PatentBatchResult` and processing continues with the next
        patent — no patent failure aborts the batch.

        The returned list is guaranteed to have the same length as *patents*
        and the same positional ordering (``results[i]`` corresponds to
        ``patents[i]``).

        .. note:: **Parallel execution hook**

           The loop body delegates entirely to :meth:`_analyse_one`.  To add
           parallel execution, replace the ``for`` loop with a
           ``concurrent.futures.ThreadPoolExecutor`` (or ``asyncio.gather``)
           call on ``_analyse_one`` — no other changes are needed.

        Args:
            patents: Ordered list of patent inputs to analyse.  May be empty,
                in which case an empty list is returned immediately.

        Returns:
            A list of :class:`PatentBatchResult` objects in the same order as
            the input.  Each item has either ``result`` (success) or ``error``
            (failure) populated — never both, never neither.

        Example::

            batch = service.analyse_batch([patent_a, patent_b, patent_c])
            for item in batch:
                if item.success:
                    print(f"[{item.index}] {item.patent_title}: {item.result.risk_level}")
                else:
                    print(f"[{item.index}] {item.patent_title}: FAILED — {item.error}")
        """
        if not patents:
            return []

        logger.info(
            "Starting batch analysis",
            extra={"total": len(patents)},
        )

        outcomes: list[PatentBatchResult] = []

        # Sequential loop — swap this for ThreadPoolExecutor.map(_analyse_one, ...)
        # when parallel execution is needed.  _analyse_one's signature is
        # intentionally (patent, index) -> PatentBatchResult to make mapping easy.
        for idx, patent in enumerate(patents):
            outcomes.append(self._analyse_one(patent, index=idx))

        successes = sum(1 for o in outcomes if o.success)
        failures  = len(outcomes) - successes
        logger.info(
            "Batch analysis complete",
            extra={"total": len(patents), "successes": successes, "failures": failures},
        )
        return outcomes

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _analyse_one(
        self,
        patent: PatentAnalysisInput,
        index: int = 0,
    ) -> PatentBatchResult:
        """Analyse a single patent and return a :class:`PatentBatchResult`.

        This is the core unit of work shared by both :meth:`analyse` (which
        unwraps the result or re-raises the error) and :meth:`analyse_batch`
        (which collects the outcome without raising).

        The ``(patent, index) -> PatentBatchResult`` signature is deliberately
        simple so it can be passed directly to ``executor.map`` or
        ``asyncio.gather`` when parallel execution is introduced.

        Args:
            patent: Patent input to analyse.
            index: Position of this patent in the originating list.  Stored
                verbatim in :attr:`PatentBatchResult.index`.

        Returns:
            A :class:`PatentBatchResult` with either ``result`` or ``error``
            populated.
        """
        logger.info(
            "Analysing patent",
            extra={
                "index": index,
                "patent_title": patent.patent_title,
                "assignee": patent.assignee,
                "smiles_length": len(patent.smiles),
            },
        )

        try:
            result = self._invoke_with_retry(patent)
        except _TRANSIENT_EXCEPTIONS as exc:
            msg = (
                f"Transient LLM error persisted after {self._max_attempts} attempts "
                f"for patent '{patent.patent_title}': {exc}"
            )
            logger.error(msg, exc_info=True)
            wrapped = TransientLLMError(msg)
            wrapped.__cause__ = exc
            return PatentBatchResult(index=index, patent_title=patent.patent_title, error=wrapped)
        except APIStatusError as exc:
            msg = (
                f"Non-retryable LLM API error (HTTP {exc.status_code}) "
                f"for patent '{patent.patent_title}': {exc.message}"
            )
            logger.error(msg, exc_info=True)
            wrapped = PermanentLLMError(msg)
            wrapped.__cause__ = exc
            return PatentBatchResult(index=index, patent_title=patent.patent_title, error=wrapped)
        except ValidationError as exc:
            msg = (
                f"LLM output failed Pydantic validation for patent "
                f"'{patent.patent_title}': {exc}"
            )
            logger.error(msg, exc_info=True)
            wrapped = OutputValidationError(msg)
            wrapped.__cause__ = exc
            return PatentBatchResult(index=index, patent_title=patent.patent_title, error=wrapped)
        except Exception as exc:
            msg = (
                f"Unexpected error during analysis of patent "
                f"'{patent.patent_title}': {exc}"
            )
            logger.error(msg, exc_info=True)
            wrapped = PatentAnalysisError(msg)
            wrapped.__cause__ = exc
            return PatentBatchResult(index=index, patent_title=patent.patent_title, error=wrapped)

        logger.info(
            "Patent analysis completed",
            extra={
                "index": index,
                "patent_title": patent.patent_title,
                "risk_level": result.risk_level.value,
                "confidence": result.confidence,
            },
        )
        return PatentBatchResult(index=index, patent_title=patent.patent_title, result=result)

    def _invoke_with_retry(self, patent: PatentAnalysisInput) -> PatentAnalysisResult:
        """Invoke the chain with automatic retry on transient errors.

        Uses *tenacity* to apply exponential back-off.  A new chain is built
        on each call so that the method remains thread-safe.
        """
        # Lazy import to break the circular dependency at module-load time:
        # analysis.service is imported by analysis.__init__, which is in turn
        # imported by chains.patent_analysis — importing chains here at the
        # function level avoids that cycle.
        from chains.patent_analysis import (  # noqa: PLC0415
            PatentAnalysisInput as _PatentAnalysisInput,
            build_structured_patent_analysis_chain,
        )

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
        def _call() -> PatentAnalysisResult:
            chain = build_structured_patent_analysis_chain(
                model_name=self._model_name,
                temperature=self._temperature,
                top_p=self._top_p,
                max_tokens=self._max_tokens,
                seed=self._seed,
            )
            return chain.invoke(patent.to_prompt_dict())

        return _call()


# ---------------------------------------------------------------------------
# Public API — re-exported for callers that import directly from this module
# ---------------------------------------------------------------------------

__all__ = [
    "PatentAnalysisService",
    "PatentBatchResult",
    "PatentAnalysisError",
    "TransientLLMError",
    "PermanentLLMError",
    "OutputValidationError",
]
