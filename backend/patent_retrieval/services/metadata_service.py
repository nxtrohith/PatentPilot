"""Resolve chemical IDs to patent documents and fetch full metadata.

Responsibilities:
- Query /search/documents_for_structures to get patent IDs per chemical.
- Propagate similarity scores from chemicals to patents.
- Batch-fetch full patent details via /document/batch.
"""
from __future__ import annotations

import json as _json
import logging
from typing import Any, Dict, List, Optional, Tuple

import requests

from .batch_fetcher import BatchDocumentFetcher
from ..core import RetrievalConfig, SureChemblSession
from ..models import ChemicalMatch, RetrievalError
from .patent_enrichment import enrich_patent, extract_batch_patents
from ..utils import extract_documents, values_for_keys

logger = logging.getLogger(__name__)

_PATENT_ID_KEYS = frozenset({
    "doc_id", "docid", "document_id", "documentid",
    "patent_id", "patentid",
})

# Encoding strategies to probe for the chemicalIds query parameter.
_ENCODINGS = ("repeated", "comma-separated", "json-array")


def retrieve_patent_ids_for_chemicals(
    session: SureChemblSession,
    config: RetrievalConfig,
    chemical_matches: List[ChemicalMatch],
    limit: int,
) -> List[Tuple[str, Optional[float]]]:
    """Resolve chemical matches to (patent_id, similarity_score) pairs.

    Iterates through chemicals ordered by similarity score (highest first).
    Each new patent is assigned the score of the first chemical that yielded
    it, which is the best possible score for that patent.  Stops once
    ``limit`` unique patents have been collected or all chemicals are
    exhausted.

    Returns:
        List of (patent_id, score) tuples sorted by score descending.
    """
    patent_to_score: Dict[str, Optional[float]] = {}
    max_chemicals = config.max_chemicals_to_query

    for match in chemical_matches[:max_chemicals]:
        if len(patent_to_score) >= limit:
            break

        try:
            ids = _query_patents_for_chemical(session, config, match.chemical_id)
        except (RetrievalError, requests.RequestException) as exc:
            logger.warning(
                "Could not retrieve patents for chemical %s: %s",
                match.chemical_id, exc,
            )
            continue

        new = 0
        for pid in ids:
            if pid not in patent_to_score:
                patent_to_score[pid] = match.similarity_score
                new += 1

        logger.debug(
            "Chemical %s (score=%s): %d patents found, %d new.",
            match.chemical_id,
            f"{match.similarity_score:.3f}" if match.similarity_score is not None else "N/A",
            len(ids), new,
        )

    ordered = sorted(
        patent_to_score.items(),
        key=lambda kv: (kv[1] is None, -(kv[1] or 0.0)),
    )
    logger.info(
        "Resolved %d unique patent ID(s) from %d chemical(s).",
        len(ordered), min(len(chemical_matches), max_chemicals),
    )
    return ordered


def fetch_patent_details(
    session: SureChemblSession,
    config: RetrievalConfig,
    patent_ids: List[str],
) -> List[Dict[str, Any]]:
    """Batch-fetch full patent details and return enriched flat records.

    Uses BatchDocumentFetcher for chunked retrieval with per-chunk failure
    isolation.  Records are normalised by enrich_patent.
    """
    if not patent_ids:
        return []

    logger.info(
        "Fetching details for %d patent(s) via /document/batch.", len(patent_ids)
    )
    fetcher = BatchDocumentFetcher(session, config)
    raw_response = fetcher.fetch(patent_ids)

    enriched = extract_batch_patents(raw_response)
    if not enriched:
        enriched = extract_documents(raw_response)
        logger.debug(
            "extract_batch_patents returned nothing; fell back to %d generic document(s).",
            len(enriched),
        )

    logger.info("Fetched and enriched %d patent detail record(s).", len(enriched))
    return enriched


# --------------------------------------------------------------------------- #
# Internal helpers                                                              #
# --------------------------------------------------------------------------- #

def _query_patents_for_chemical(
    session: SureChemblSession,
    config: RetrievalConfig,
    chemical_id: str,
) -> List[str]:
    """Return deduplicated patent IDs for one chemical, trying multiple encodings."""
    endpoint = f"{config.base_url}/search/documents_for_structures"
    page_size = min(config.page_size, config.max_results)

    for strategy in _ENCODINGS:
        params = _build_params(strategy, [chemical_id], page=1, page_size=page_size)
        try:
            response = session.json_request("POST", endpoint, params=params)
        except requests.RequestException as exc:
            logger.debug(
                "Encoding %r failed for chemical %s: %s", strategy, chemical_id, exc
            )
            continue

        patent_ids = values_for_keys(response, _PATENT_ID_KEYS)
        if patent_ids:
            logger.debug(
                "Chemical %s: %d patent ID(s) via %r encoding.",
                chemical_id, len(patent_ids), strategy,
            )
            return list(dict.fromkeys(patent_ids))  # deduplicate, preserve order

    logger.debug("No patent IDs found for chemical %s.", chemical_id)
    return []


def _build_params(
    strategy: str,
    chemical_ids: List[str],
    page: int,
    page_size: int,
) -> Any:
    """Build query parameters for one chemicalIds encoding strategy."""
    if strategy == "repeated":
        return (
            [("chemicalIds", cid) for cid in chemical_ids]
            + [("page", page), ("itemsPerPage", page_size)]
        )
    if strategy == "comma-separated":
        return {
            "chemicalIds": ",".join(chemical_ids),
            "page": page,
            "itemsPerPage": page_size,
        }
    # json-array
    return {
        "chemicalIds": _json.dumps(chemical_ids),
        "page": page,
        "itemsPerPage": page_size,
    }
