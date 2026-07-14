"""Orchestrates the full deterministic patent reduction & ranking pipeline.

    Step 1  Remove exact duplicates            -> DuplicateReducer
    Step 2  Collapse patent families           -> FamilyReducer
    Step 3  Structural similarity score        -> StructuralScorer
    Step 4  Chemical evidence score            -> ChemicalEvidenceScorer
    Step 5  Claim importance score             -> ClaimImportanceScorer
    Step 6  Legal status score                 -> LegalStatusScorer
    Step 7  Publication recency score          -> RecencyScorer
    Step 8  Composite score                    -> PatentRanker
    Step 9  Ranking                            -> PatentRanker
    Step 10 Filtering (MIN_SCORE, MAX_PATENTS) -> PatentRanker
    Step 11 Statistics                         -> PipelineStatistics

No LLM calls, summaries, or patentability reports are produced here; this
module only performs deterministic filtering and ranking.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from patent_reduction.config import ReductionConfig
from patent_reduction.models import PatentRecord, PipelineStatistics, ReductionResult
from patent_reduction.ranking.patent_ranker import PatentRanker
from patent_reduction.reducers.duplicate_reducer import DuplicateReducer
from patent_reduction.reducers.family_reducer import FamilyReducer
from patent_reduction.scoring.chemical_score import ChemicalEvidenceScorer
from patent_reduction.scoring.claim_score import ClaimImportanceScorer
from patent_reduction.scoring.legal_score import LegalStatusScorer
from patent_reduction.scoring.recency_score import RecencyScorer
from patent_reduction.scoring.structural_score import StructuralScorer

logger = logging.getLogger(__name__)


class PatentReductionPipeline:
    """Reduces a raw SureChEMBL patent list into a small, ranked shortlist."""

    def __init__(
        self,
        config: Optional[ReductionConfig] = None,
        duplicate_reducer: Optional[DuplicateReducer] = None,
        family_reducer: Optional[FamilyReducer] = None,
        ranker: Optional[PatentRanker] = None,
    ) -> None:
        self.config = config or ReductionConfig()
        self.duplicate_reducer = duplicate_reducer or DuplicateReducer()
        self.family_reducer = family_reducer or FamilyReducer(self.config.family)
        self.ranker = ranker or PatentRanker(
            weights=self.config.weights,
            filters=self.config.filters,
            structural_scorer=StructuralScorer(self.config.structural),
            chemical_scorer=ChemicalEvidenceScorer(self.config.chemical_evidence),
            claim_scorer=ClaimImportanceScorer(self.config.claim_importance),
            legal_scorer=LegalStatusScorer(self.config.legal),
            recency_scorer=RecencyScorer(self.config.recency),
        )

    def run(self, raw_patents: List[Dict[str, Any]]) -> ReductionResult:
        stats = PipelineStatistics()
        stats.initial_patents = len(raw_patents)
        logger.info("PatentReductionPipeline: received %d raw patents.", stats.initial_patents)

        patents = self._normalize(raw_patents)

        deduped = self.duplicate_reducer.reduce(patents)
        stats.after_duplicate_removal = len(deduped)

        representatives = self.family_reducer.reduce(deduped)
        stats.after_family_collapse = len(representatives)

        ranked, filtered = self.ranker.rank_and_filter(representatives)
        stats.after_score_filtering = len(filtered)
        stats.final_patents = len(filtered)

        logger.info(
            "PatentReductionPipeline funnel: initial=%d -> dedup=%d -> family=%d -> filtered=%d",
            stats.initial_patents,
            stats.after_duplicate_removal,
            stats.after_family_collapse,
            stats.after_score_filtering,
        )

        return ReductionResult(reduced_patents=filtered, statistics=stats)

    @staticmethod
    def _normalize(raw_patents: List[Dict[str, Any]]) -> List[PatentRecord]:
        normalized: List[PatentRecord] = []
        for raw in raw_patents:
            try:
                normalized.append(PatentRecord.from_raw(raw))
            except TypeError as exc:
                logger.warning("Skipping unparseable patent object: %s", exc)
        return normalized
