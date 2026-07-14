"""Step 3: structural similarity score, normalized 0-100."""

from __future__ import annotations

import logging
from typing import Optional

from patent_reduction.config import StructuralScoreConfig
from patent_reduction.models import PatentRecord

logger = logging.getLogger(__name__)


class StructuralScorer:
    """Normalizes SureChEMBL structural similarity (0.0-1.0) into 0-100.

    Falls back to a configurable neutral default when similarity data is
    unavailable, instead of raising.
    """

    def __init__(self, config: Optional[StructuralScoreConfig] = None) -> None:
        self.config = config or StructuralScoreConfig()

    def score(self, patent: PatentRecord) -> float:
        if patent.similarity is None:
            logger.debug(
                "No similarity data for %s; using neutral default %.1f",
                patent.doc_id,
                self.config.neutral_default_score,
            )
            return self.config.neutral_default_score
        return max(0.0, min(100.0, patent.similarity * 100.0))
