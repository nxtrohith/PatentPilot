"""Step 2: collapse patent families into one representative each."""

from __future__ import annotations

import logging
from datetime import date
from typing import Dict, List, Optional, Tuple

from patent_reduction.config import FamilyConfig
from patent_reduction.models import PatentRecord

logger = logging.getLogger(__name__)

_MAX_DATE = date.max


class FamilyReducer:
    """Groups patents by family and selects one representative per family.

    Representative selection priority:
        1. Country priority (configurable, default WO > US > EP > JP > CN > other)
        2. Earliest publication date, as a tiebreaker

    The remaining family members are attached to the representative via
    ``PatentRecord.family_members`` so no information is lost.
    """

    def __init__(self, config: Optional[FamilyConfig] = None) -> None:
        self.config = config or FamilyConfig()

    def _priority(self, patent: PatentRecord) -> int:
        if not patent.country_code:
            return self.config.fallback_priority
        try:
            return self.config.country_priority.index(patent.country_code)
        except ValueError:
            return self.config.fallback_priority

    def _sort_key(self, patent: PatentRecord) -> Tuple[int, date]:
        return (self._priority(patent), patent.publication_date or _MAX_DATE)

    def reduce(self, patents: List[PatentRecord]) -> List[PatentRecord]:
        groups: Dict[str, List[PatentRecord]] = {}
        for patent in patents:
            groups.setdefault(patent.family_key, []).append(patent)

        representatives: List[PatentRecord] = []
        for family_key, members in groups.items():
            ordered = sorted(members, key=self._sort_key)
            representative = ordered[0]
            representative.family_members = [m for m in ordered if m is not representative]
            if len(ordered) > 1:
                logger.debug(
                    "Family %s collapsed %d patents into representative %s",
                    family_key,
                    len(ordered),
                    representative.doc_id,
                )
            representatives.append(representative)

        logger.info(
            "FamilyReducer collapsed %d patents into %d family representatives.",
            len(patents),
            len(representatives),
        )
        return representatives
