"""Retrieve and parse similarity-search results from SureChEMBL.

Responsible for:
- Fetching the result page from ``/search/{hash}/results``.
- Extracting chemical IDs and similarity scores from the generic response.
- Deduplicating and sorting by score descending.
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional

import requests

from .config import RetrievalConfig
from .http_session import SureChemblSession
from .models import ChemicalMatch, RetrievalError
from .utils import extract_structures, first_value_for_keys

logger = logging.getLogger(__name__)

# Keys under which SureChEMBL may return a chemical identifier.
_CHEMICAL_ID_KEYS = frozenset({
    "chemicalid",
    "chemical_id",
    "schemblid",
    "schembl_id",
    "id",
    "chemid",
    "chem_id",
})

# Keys under which SureChEMBL may return a Tanimoto or similarity score.
_SIMILARITY_SCORE_KEYS = frozenset({
    "similarity",
    "similarityscore",
    "similarity_score",
    "score",
    "tanimoto",
    "tanimotoscore",
    "tanimoto_score",
})


def retrieve_search_results(
    session: SureChemblSession,
    config: RetrievalConfig,
    search_hash: str,
) -> List[ChemicalMatch]:
    """Fetch and parse the similarity-search result page.

    Args:
        session: Configured HTTP session.
        config: Pipeline configuration.
        search_hash: Hash returned by :func:`search_service.start_similarity_search`.

    Returns:
        Deduplicated :class:`ChemicalMatch` objects sorted by similarity score
        descending.  Compounds without a score are placed at the end.

    Raises:
        RetrievalError: If the results endpoint cannot be reached or parsed.
    """
    logger.info("Fetching search results for hash %s", search_hash)

    try:
        response = session.json_request(
            "GET",
            f"{config.base_url}/search/{search_hash}/results",
            params={"page": 1, "max_results": config.max_results},
        )
    except requests.RequestException as exc:
        raise RetrievalError(
            f"Failed to retrieve search results for hash {search_hash!r}: {exc}"
        ) from exc

    structures = extract_structures(response)
    if not structures:
        logger.warning(
            "No structures in search results for hash %s. "
            "The search may have matched no compounds.",
            search_hash,
        )
        return []

    matches = _parse_chemical_matches(structures)
    logger.info(
        "Parsed %d unique chemical match(es) from %d result structure(s).",
        len(matches),
        len(structures),
    )
    return matches


def _parse_chemical_matches(structures: List[Any]) -> List[ChemicalMatch]:
    """Extract deduplicated ``ChemicalMatch`` objects from raw structure items."""
    seen: set = set()
    matches: List[ChemicalMatch] = []

    for item in structures:
        chemical_id = first_value_for_keys(item, _CHEMICAL_ID_KEYS)
        if not chemical_id or chemical_id in seen:
            continue
        seen.add(chemical_id)

        score: Optional[float] = None
        raw_score = first_value_for_keys(item, _SIMILARITY_SCORE_KEYS)
        if raw_score is not None:
            try:
                score = float(raw_score)
            except (ValueError, TypeError):
                logger.debug(
                    "Could not parse similarity score %r for chemical %s.",
                    raw_score,
                    chemical_id,
                )

        matches.append(ChemicalMatch(chemical_id=chemical_id, similarity_score=score))

    # Scored entries descend by score; unscored entries fall to the end.
    return sorted(
        matches,
        key=lambda m: (m.similarity_score is None, -(m.similarity_score or 0.0)),
    )
