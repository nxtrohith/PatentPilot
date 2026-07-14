"""Step 4: chemical evidence score, normalized 0-100."""

from __future__ import annotations

import logging
from typing import Optional

from patent_reduction.config import ChemicalEvidenceScoreConfig
from patent_reduction.models import PatentRecord

logger = logging.getLogger(__name__)


class ChemicalEvidenceScorer:
    """Scores how much chemical evidence supports a patent match.

    Combines (weighted) counts of matched chemicals, chemical annotations,
    and chemical IDs, then normalizes against a configurable cap so the
    score saturates at 100 rather than growing unbounded.
    """

    def __init__(self, config: Optional[ChemicalEvidenceScoreConfig] = None) -> None:
        self.config = config or ChemicalEvidenceScoreConfig()

    def score(self, patent: PatentRecord) -> float:
        cfg = self.config
        weighted_count = (
            len(patent.matched_chemicals) * cfg.matched_chemicals_weight
            + len(patent.annotations) * cfg.annotations_weight
            + len(patent.chemical_ids) * cfg.chemical_ids_weight
        )
        if cfg.max_evidence_for_full_score <= 0:
            logger.warning("max_evidence_for_full_score <= 0; returning 0 to avoid div-by-zero.")
            return 0.0
        normalized = (weighted_count / cfg.max_evidence_for_full_score) * 100.0
        return max(0.0, min(100.0, normalized))
