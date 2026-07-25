"""Submit a SMILES similarity search to SureChEMBL.

Responsibilities:
- Validate the SMILES string before touching the network.
- POST the search request to ``/search/structure``.
- Extract and return the search hash for downstream polling.
"""
from __future__ import annotations

import logging

import requests

from ..core import RetrievalConfig, SureChemblSession
from ..models import RetrievalError
from ..utils import first_value_for_keys

logger = logging.getLogger(__name__)


def validate_smiles(smiles: str) -> None:
    """Raise ``ValueError`` if ``smiles`` fails basic structural checks.

    This is intentionally lightweight — it catches empty inputs and strings
    that contain no alphabetic atom symbols, without attempting full chemistry-
    aware parsing.  The goal is to fail fast before a wasted network round-trip.

    Args:
        smiles: The SMILES string to validate.

    Raises:
        ValueError: If the input is empty or contains no atom characters.
    """
    if not smiles or not smiles.strip():
        raise ValueError("SMILES string cannot be empty.")
    if not any(c.isalpha() for c in smiles):
        raise ValueError(
            f"SMILES does not appear to contain any atom symbols: {smiles!r}"
        )


def start_similarity_search(
    session: SureChemblSession,
    config: RetrievalConfig,
    smiles: str,
) -> str:
    """Submit a similarity search and return the opaque search hash.

    Args:
        session: Configured, retry-enabled HTTP session.
        config: Pipeline configuration (``base_url``, ``search_type``,
            ``max_results``).
        smiles: SMILES string to search.

    Returns:
        The search hash string needed for polling and result retrieval.

    Raises:
        ValueError: If ``smiles`` fails :func:`validate_smiles`.
        RetrievalError: If SureChEMBL does not return a usable hash.
        requests.RequestException: On unrecoverable network or HTTP errors.
    """
    validate_smiles(smiles)

    payload = {
        "StructureSearchRequest": {
            "struct": smiles.strip(),
            "structSearchType": config.search_type,
            "maxResults": config.max_results,
        }
    }

    logger.info(
        "Submitting %s search for SMILES=%r (max_results=%d)",
        config.search_type,
        smiles,
        config.max_results,
    )

    try:
        response = session.json_request(
            "POST",
            f"{config.base_url}/search/structure",
            json=payload,
        )
    except requests.RequestException as exc:
        raise RetrievalError(f"Failed to submit similarity search: {exc}") from exc

    search_hash = first_value_for_keys(response, {"hash"})
    if not search_hash:
        raise RetrievalError(
            "SureChEMBL returned no search hash. "
            f"Raw response: {response}"
        )

    logger.info("Search submitted. Hash: %s", search_hash)
    return search_hash
