"""Steps 8-10: composite score, ranking, and score/count filtering."""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

from patent_reduction.config import CompositeWeights, FilterConfig
from patent_reduction.models import PatentRecord, RankedPatent, ScoreBreakdown
from patent_reduction.scoring.chemical_score import ChemicalEvidenceScorer
from patent_reduction.scoring.claim_score import ClaimImportanceScorer
from patent_reduction.scoring.legal_score import LegalStatusScorer
from patent_reduction.scoring.recency_score import RecencyScorer
from patent_reduction.scoring.structural_score import StructuralScorer

logger = logging.getLogger(__name__)


class PatentRanker:
    """Computes per-patent scores, combines them, ranks, and filters."""

    def __init__(
        self,
        weights: Optional[CompositeWeights] = None,
        filters: Optional[FilterConfig] = None,
        structural_scorer: Optional[StructuralScorer] = None,
        chemical_scorer: Optional[ChemicalEvidenceScorer] = None,
        claim_scorer: Optional[ClaimImportanceScorer] = None,
        legal_scorer: Optional[LegalStatusScorer] = None,
        recency_scorer: Optional[RecencyScorer] = None,
    ) -> None:
        self.weights = weights or CompositeWeights()
        self.filters = filters or FilterConfig()
        self.structural_scorer = structural_scorer or StructuralScorer()
        self.chemical_scorer = chemical_scorer or ChemicalEvidenceScorer()
        self.claim_scorer = claim_scorer or ClaimImportanceScorer()
        self.legal_scorer = legal_scorer or LegalStatusScorer()
        self.recency_scorer = recency_scorer or RecencyScorer()

    def _score_one(self, patent: PatentRecord) -> ScoreBreakdown:
        structure = self.structural_scorer.score(patent)
        chemical_evidence = self.chemical_scorer.score(patent)
        claim_importance = self.claim_scorer.score(patent)
        legal = self.legal_scorer.score(patent)
        recency = self.recency_scorer.score(patent)

        w = self.weights
        final = (
            structure * w.structure
            + chemical_evidence * w.chemical_evidence
            + claim_importance * w.claim_importance
            + legal * w.legal
            + recency * w.recency
        )
        final = max(0.0, min(100.0, final))

        return ScoreBreakdown(
            structure=structure,
            chemical_evidence=chemical_evidence,
            claim_importance=claim_importance,
            legal=legal,
            recency=recency,
            final=final,
        )

    def score_all(self, patents: List[PatentRecord]) -> List[Tuple[PatentRecord, ScoreBreakdown]]:
        return [(patent, self._score_one(patent)) for patent in patents]

    def rank(self, scored_patents: List[Tuple[PatentRecord, ScoreBreakdown]]) -> List[RankedPatent]:
        ordered = sorted(scored_patents, key=lambda item: item[1].final, reverse=True)
        return [
            RankedPatent(
                representative=patent,
                family_members=list(patent.family_members),
                scores=scores,
                rank=index + 1,
            )
            for index, (patent, scores) in enumerate(ordered)
        ]

    def filter(self, ranked_patents: List[RankedPatent]) -> List[RankedPatent]:
        above_threshold = [rp for rp in ranked_patents if rp.scores.final >= self.filters.min_score]
        logger.info(
            "PatentRanker: %d/%d patents met MIN_SCORE=%.1f",
            len(above_threshold),
            len(ranked_patents),
            self.filters.min_score,
        )
        limited = above_threshold[: self.filters.max_patents]
        # Re-assign contiguous rank numbers after filtering.
        for index, ranked_patent in enumerate(limited):
            ranked_patent.rank = index + 1
        return limited

    def rank_and_filter(self, patents: List[PatentRecord]) -> Tuple[List[RankedPatent], List[RankedPatent]]:
        """Returns (all_ranked_before_filtering, final_filtered) for stats."""
        scored = self.score_all(patents)
        ranked = self.rank(scored)
        filtered = self.filter(ranked)
        return ranked, filtered
