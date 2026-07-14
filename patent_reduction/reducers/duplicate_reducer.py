"""Step 1: remove exact duplicate patents by doc_id."""

from __future__ import annotations

import logging
from typing import List

from patent_reduction.models import PatentRecord

logger = logging.getLogger(__name__)


class DuplicateReducer:
    """Keeps only the first occurrence of each ``doc_id``."""

    def reduce(self, patents: List[PatentRecord]) -> List[PatentRecord]:
        seen: set = set()
        deduped: List[PatentRecord] = []
        for patent in patents:
            if patent.doc_id in seen:
                continue
            seen.add(patent.doc_id)
            deduped.append(patent)

        removed = len(patents) - len(deduped)
        if removed:
            logger.info("DuplicateReducer removed %d duplicate patent(s).", removed)
        return deduped
