"""Step 7: publication recency score."""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from patent_reduction.config import RecencyScoreConfig
from patent_reduction.models import PatentRecord

logger = logging.getLogger(__name__)


class RecencyScorer:
    """Awards a bonus for recently published patents based on age buckets."""

    def __init__(self, config: Optional[RecencyScoreConfig] = None, today: Optional[date] = None) -> None:
        self.config = config or RecencyScoreConfig()
        self._today = today

    def _current_date(self) -> date:
        return self._today or date.today()

    def score(self, patent: PatentRecord) -> float:
        if patent.publication_date is None:
            logger.debug("No publication date for %s; using unknown default.", patent.doc_id)
            return self.config.unknown_date_score

        years = (self._current_date() - patent.publication_date).days / 365.25
        for max_years, bucket_score in self.config.buckets:
            if years <= max_years:
                return bucket_score
        return self.config.older_score
