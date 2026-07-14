"""Step 5: claim importance score, normalized 0-100.

Determines where the matched chemicals occur (claims > abstract > title >
description) and combines section weights into a single 0-100 score.
"""

from __future__ import annotations

import logging
import re
from typing import Iterable, Optional

from patent_reduction.config import ClaimImportanceScoreConfig
from patent_reduction.models import PatentRecord

logger = logging.getLogger(__name__)


def _search_terms(patent: PatentRecord) -> list:
    """Extract textual search terms for the chemicals matched to this patent."""
    terms = []
    for source in (patent.matched_chemicals, patent.chemical_ids):
        for item in source:
            if isinstance(item, dict):
                for key in ("name", "chemical_id", "id", "smiles"):
                    value = item.get(key)
                    if value:
                        terms.append(str(value))
            elif item is not None:
                terms.append(str(item))
    return [t.strip() for t in terms if t and t.strip()]


def _mentioned(text: str, terms: Iterable[str]) -> bool:
    if not text:
        return False
    lowered = text.lower()
    for term in terms:
        if not term:
            continue
        pattern = re.escape(term.lower())
        if re.search(pattern, lowered):
            return True
    return False


class ClaimImportanceScorer:
    """Scores a patent by where its matched chemicals appear in the text."""

    def __init__(self, config: Optional[ClaimImportanceScoreConfig] = None) -> None:
        self.config = config or ClaimImportanceScoreConfig()

    def score(self, patent: PatentRecord) -> float:
        cfg = self.config
        terms = _search_terms(patent)
        if not terms:
            logger.debug("No chemical search terms for %s; claim importance is 0.", patent.doc_id)
            return 0.0

        weight_total = 0.0
        if _mentioned(patent.claims, terms):
            weight_total += cfg.claims_weight
        if _mentioned(patent.abstract, terms):
            weight_total += cfg.abstract_weight
        if _mentioned(patent.title, terms):
            weight_total += cfg.title_weight
        if _mentioned(patent.description, terms):
            weight_total += cfg.description_weight

        max_possible = cfg.max_possible
        if max_possible <= 0:
            return 0.0
        return max(0.0, min(100.0, (weight_total / max_possible) * 100.0))
