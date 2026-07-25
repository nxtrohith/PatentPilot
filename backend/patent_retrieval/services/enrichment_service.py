"""Enrich missing patent abstracts from Google Patents.

When SureChEMBL does not return an abstract, this module fetches one from
the public Google Patents page identified by the patent's publication number.

No extra dependencies are required beyond ``requests`` (already a project
dependency).  The implementation parses Google Patents' embedded JSON-LD
structured-data block first, then falls back to the ``<meta
name="description">`` tag.  Both paths use only the standard library
(``re``, ``html``, ``json``).

Failure modes are handled silently at ``DEBUG`` level so a single
unavailable abstract never aborts the pipeline.
"""
from __future__ import annotations

import html as _html
import json
import logging
import re
from typing import List, Optional

import requests

from ..core import RetrievalConfig
from ..models import PatentResult

logger = logging.getLogger(__name__)

_GOOGLE_PATENTS_BASE = "https://patents.google.com/patent"

# Matches <script type="application/ld+json">…</script> (lazy, DOTALL).
_LD_JSON_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)
# Matches <meta name="description" content="…">
_META_DESC_RE = re.compile(
    r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']',
    re.IGNORECASE,
)
# Strip hyphens and spaces from publication numbers before building the URL.
_PUB_STRIP_RE = re.compile(r"[\s\-]+")


def enrich_missing_abstracts(
    patents: List[PatentResult],
    config: RetrievalConfig,
) -> List[PatentResult]:
    """Back-fill missing abstracts from Google Patents where possible.

    Patents that already have a non-empty abstract are returned unchanged.
    For patents without an abstract, a fetch is attempted using the
    ``publication_number`` (falling back to ``document_id``).  On success the
    ``abstract`` field is set and ``source`` is updated to ``"Google Patents"``.

    Args:
        patents: List of patent results from the SureChEMBL pipeline.
        config: Pipeline configuration (uses ``google_patents_timeout``).

    Returns:
        The same list, with abstracts back-filled in place where possible.
    """
    missing = [p for p in patents if not (p.abstract and p.abstract.strip())]
    if not missing:
        return patents

    logger.info(
        "%d/%d patent(s) have no abstract; attempting Google Patents enrichment.",
        len(missing), len(patents),
    )

    enriched_count = 0
    for patent in missing:
        pub_number = patent.publication_number or patent.document_id
        if not pub_number:
            logger.debug("Skipping enrichment: no publication number or document ID.")
            continue

        abstract = _fetch_google_abstract(pub_number, config.google_patents_timeout)
        if abstract:
            patent.abstract = abstract
            patent.source   = "Google Patents"
            enriched_count += 1
            logger.info(
                "Enriched abstract for %s from Google Patents (%d chars).",
                pub_number, len(abstract),
            )
        else:
            logger.debug(
                "No abstract found on Google Patents for %s.", pub_number
            )

    if enriched_count:
        logger.info(
            "Enrichment complete: %d/%d abstract(s) filled from Google Patents.",
            enriched_count, len(missing),
        )

    return patents


# --------------------------------------------------------------------------- #
# Internal helpers                                                              #
# --------------------------------------------------------------------------- #

def _fetch_google_abstract(
    publication_number: str,
    timeout: float,
) -> Optional[str]:
    """Retrieve the abstract for one publication number from Google Patents.

    Returns the abstract string, or ``None`` if not found or any error occurs.
    Never raises; all failures are logged at ``DEBUG`` level.
    """
    normalized = _PUB_STRIP_RE.sub("", publication_number).upper()
    url = f"{_GOOGLE_PATENTS_BASE}/{normalized}"

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; PatentPilot/1.0; "
                    "patent-retrieval-pipeline)"
                )
            },
            allow_redirects=True,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.debug(
            "Google Patents request failed for %s: %s", publication_number, exc
        )
        return None

    return (
        _parse_ld_json_abstract(response.text)
        or _parse_meta_description(response.text)
    )


def _parse_ld_json_abstract(html_text: str) -> Optional[str]:
    """Extract the abstract from the JSON-LD structured-data block."""
    for match in _LD_JSON_RE.finditer(html_text):
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        value = data.get("abstract") or data.get("description")
        if value and isinstance(value, str):
            return _html.unescape(value.strip()) or None
    return None


def _parse_meta_description(html_text: str) -> Optional[str]:
    """Extract the abstract from the ``<meta name="description">`` tag."""
    match = _META_DESC_RE.search(html_text)
    if match:
        text = _html.unescape(match.group(1).strip())
        return text or None
    return None
