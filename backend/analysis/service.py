"""Patent analysis service for PatentPilot.

This module is the single, authoritative entry-point for running LLM-powered
patent analysis on one or more patent documents.  It is intentionally decoupled
from:

- **UI / presentation** — the service returns typed Pydantic objects; callers
  decide how to display them.
- **Retrieval** — the service accepts pre-fetched
  :class:`~chains.patent_analysis.PatentAnalysisInput` objects; callers decide
  how to source patents.

Usage — single patent::

    from llm.provider import get_llm
    from chains.patent_analysis import PatentAnalysisInput
    from analysis.service import PatentAnalysisService

    llm = get_llm()
    service = PatentAnalysisService(llm)
    result = service.analyse(
        PatentAnalysisInput(
            smiles="CC(=O)Oc1ccccc1C(=O)O",
            patent_title="Novel salicylate derivatives ...",
            patent_abstract="The present invention relates to ...",
            publication_date="2022-03-10",
            assignee="Pharma Corp Ltd",
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

from analysis.schema import PatentAnalysisResult
from analysis.base_service import BaseLLMService

if TYPE_CHECKING:
    from chains.patent_analysis import PatentAnalysisInput

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Batch result container
# ---------------------------------------------------------------------------


@dataclass
class PatentBatchResult:
    """Outcome for one patent within a batch analysis run.

    Attributes:
        index: Zero-based position of this patent in the original input list.
        patent_title: Title of the patent.
        result: The validated :class:`~analysis.schema.PatentAnalysisResult`
            if analysis succeeded; ``None`` otherwise.
        error: The exception raised if analysis failed; ``None`` on success.
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


class PatentAnalysisService(BaseLLMService):
    """Orchestrates LLM-based analysis for one or many patent documents.
    
    Inherits robust retry logic from BaseLLMService.
    """

    def analyse(self, patent: PatentAnalysisInput) -> PatentAnalysisResult:
        """Analyse a single patent and return a validated result."""
        outcome = self._analyse_one(patent, index=0)
        if outcome.failure:
            raise outcome.error  # type: ignore[misc]
        return outcome.result  # type: ignore[return-value]

    def analyse_batch(
        self,
        patents: list[PatentAnalysisInput],
    ) -> list[PatentBatchResult]:
        """Analyse a list of patents, continuing past individual failures."""
        if not patents:
            return []

        logger.info(
            "Starting batch analysis",
            extra={"total": len(patents)},
        )

        outcomes: list[PatentBatchResult] = []

        # Sequential loop — swap this for ThreadPoolExecutor.map(_analyse_one, ...)
        # when parallel execution is needed.
        for idx, patent in enumerate(patents):
            outcomes.append(self._analyse_one(patent, index=idx))

        successes = sum(1 for o in outcomes if o.success)
        failures  = len(outcomes) - successes
        logger.info(
            "Batch analysis complete",
            extra={"total": len(patents), "successes": successes, "failures": failures},
        )
        return outcomes

    def _analyse_one(
        self,
        patent: PatentAnalysisInput,
        index: int = 0,
    ) -> PatentBatchResult:
        """Analyse a single patent with retry logic and return a PatentBatchResult."""
        logger.info(
            "Analysing patent",
            extra={
                "index": index,
                "patent_title": patent.patent_title,
                "assignee": patent.assignee,
            },
        )

        # Lazy import to break the circular dependency at module-load time
        from chains.patent_analysis import build_structured_patent_analysis_chain

        def _call_chain() -> PatentAnalysisResult:
            chain = build_structured_patent_analysis_chain(self.llm)
            return chain.invoke(patent.to_prompt_dict())

        try:
            result = self._execute_with_retry(
                _call_chain,
                context_msg=f"patent analysis for '{patent.patent_title}'"
            )
        except Exception as exc:
            return PatentBatchResult(index=index, patent_title=patent.patent_title, error=exc)

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

__all__ = [
    "PatentAnalysisService",
    "PatentBatchResult",
]
