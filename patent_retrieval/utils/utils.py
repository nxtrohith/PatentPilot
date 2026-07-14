"""Shared utility functions for the retrieval and reduction pipelines.

Functions here are deliberately loose because the SureChEMBL responses leave
``data`` generic.  They walk nested structures to extract identifiers, document
objects, and metadata without assuming a fixed schema.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


def walk(value: Any) -> Iterable[tuple]:
    """Yield (key, value) pairs recursively without assuming data's shape."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def values_for_keys(data: Any, keys: set) -> List[str]:
    """Return all unique primitive values matching the supplied key set."""
    values = []
    for key, value in walk(data):
        if str(key).lower() in keys and isinstance(value, (str, int)):
            text = str(value)
            if text not in values:
                values.append(text)
    return values


def first_value_for_keys(data: Any, keys: set) -> Optional[str]:
    values = values_for_keys(data, keys)
    return values[0] if values else None


def extract_structures(data: Any) -> List[Any]:
    """Return structure objects from a structure-search response."""
    if not isinstance(data, dict):
        return []
    response_data = data.get("data")
    if not isinstance(response_data, dict):
        return []
    results = response_data.get("results")
    if not isinstance(results, dict):
        return []
    structures = results.get("structures")
    return structures if isinstance(structures, list) else []


def extract_ids(items: Iterable[Any], keys: set) -> List[str]:
    found = []
    for item in items:
        for value in values_for_keys(item, keys):
            if value not in found:
                found.append(value)
    return found


def response_has_documents(data: Any) -> bool:
    """Return True only when a response contains a non-empty documents list."""
    return any(
        str(key).lower() == "documents"
        and isinstance(value, list)
        and bool(value)
        for key, value in walk(data)
    )


def patent_count(data: Any) -> Optional[int]:
    """Return SureChEMBL's total matching patent-document count, if present."""
    if not isinstance(data, dict):
        return None
    results = data.get("data", {}).get("results", {})
    if not isinstance(results, dict):
        return None
    total_hits = results.get("total_hits")
    if isinstance(total_hits, int):
        return total_hits
    if isinstance(total_hits, str) and total_hits.isdigit():
        return int(total_hits)
    return None


def doc_id_for_record(record: Dict[str, Any]) -> Optional[str]:
    """Return a plausible document identifier from one patent-like object."""
    return first_value_for_keys(
        record,
        {
            "doc_id",
            "docid",
            "document_id",
            "documentid",
            "patent_id",
            "patentid",
        },
    )


def extract_documents(data: Any) -> List[Dict[str, Any]]:
    """Extract patent document objects from a loose SureChEMBL response shape."""
    documents: List[Dict[str, Any]] = []
    for key, value in walk(data):
        if str(key).lower() != "documents" or not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, dict):
                documents.append(item)
    return documents


def merge_documents_by_doc_id(
    base_documents: List[Dict[str, Any]],
    detail_documents: List[Dict[str, Any]],
    chemical_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Merge search-result docs with detail docs without losing match evidence.

    ``documents_for_structures`` may contain match evidence while ``document/batch``
    may contain richer bibliographic/text fields.  This joins both by ``doc_id``
    and backfills queried chemical IDs as evidence when SureChEMBL omits them.
    """
    merged: Dict[str, Dict[str, Any]] = {}

    for record in base_documents + detail_documents:
        doc_id = doc_id_for_record(record)
        if not doc_id:
            continue
        current = merged.setdefault(doc_id, {})
        current.update(record)
        current.setdefault("doc_id", doc_id)

    if chemical_ids:
        for record in merged.values():
            record.setdefault("chemical_ids", chemical_ids)
            record.setdefault("matched_chemicals", chemical_ids)

    return list(merged.values())
