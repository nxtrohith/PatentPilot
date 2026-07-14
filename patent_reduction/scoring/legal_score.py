"""Step 6: legal status score.

Rather than discarding expired/rejected patents, this assigns a (possibly
negative) point delta per legal-status keyword. All deltas are configurable.
"""

from __future__ import annotations

import logging
from typing import Optional

from patent_reduction.config import LegalStatusScoreConfig
from patent_reduction.models import PatentRecord

logger = logging.getLogger(__name__)


class LegalStatusScorer:
    """Maps a patent's legal status text to a configurable point delta."""

    def __init__(self, config: Optional[LegalStatusScoreConfig] = None) -> None:
        self.config = config or LegalStatusScoreConfig()

    def score(self, patent: PatentRecord) -> float:
        cfg = self.config
        status_text = (patent.legal_status or "").lower()
        if not status_text:
            logger.debug("No legal status for %s; using unknown default.", patent.doc_id)
            return cfg.unknown_status_score

        for keyword, points in cfg.status_points.items():
            if keyword.lower() in status_text:
                return max(cfg.min_score, min(cfg.max_score, points))

        logger.debug("Unrecognized legal status %r for %s; using unknown default.", status_text, patent.doc_id)
        return cfg.unknown_status_score
