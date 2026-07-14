"""MongoDB persistence layer for PatentResult objects.

Provides ``save_patents`` and ``load_patents`` so the pipeline can store
results for later retrieval without duplicates (upsert on ``publication_number``).

Collections used
----------------
``patentpilot.patents``
    One document per patent.  ``publication_number`` is the natural key and
    is used as the upsert filter.

Example::

    from patent_retrieval.storage_service import save_patents, load_patents

    patents = pipeline.run("CC(=O)Oc1ccccc1C(=O)O")
    save_patents(patents, query_smiles="CC(=O)Oc1ccccc1C(=O)O")

    results = load_patents(query_smiles="CC(=O)Oc1ccccc1C(=O)O")
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

from pymongo import UpdateOne

from .db import get_db
from ..models import PatentResult

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION = "patents"


def _get_collection_name(query_smiles: Optional[str]) -> str:
    """Map a query SMILES to a sanitized collection name.
    
    If no SMILES is provided, falls back to the default collection name.
    """
    if not query_smiles:
        return DEFAULT_COLLECTION
    
    # Sanitize characters that are invalid or problematic in MongoDB collection names
    # (e.g., $, ., null byte, and common symbols like parentheses/equals for readability)
    sanitized = re.sub(r'[\s\.\$/\\=\(\)\+#\-]', '_', query_smiles)
    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized).strip('_')
    
    return f"patents_{sanitized}"


def save_patents(
    patents: List[PatentResult],
    *,
    query_smiles: Optional[str] = None,
) -> int:
    """Upsert a list of :class:`PatentResult` objects into MongoDB.

    Saves patents in a dynamic collection (folder) named after the query_smiles.

    Args:
        patents: Patent results to persist.
        query_smiles: Optional SMILES string used to determine the collection
            (folder) and tag the documents.

    Returns:
        Number of documents upserted or modified.
    """
    if not patents:
        return 0

    db = get_db()
    coll_name = _get_collection_name(query_smiles)
    collection = db[coll_name]

    # Ensure a unique index on publication_number exists in this collection.
    collection.create_index("publication_number", unique=True, sparse=True)

    now = datetime.now(timezone.utc)
    ops: List[UpdateOne] = []

    for patent in patents:
        if not patent.publication_number:
            logger.debug("Skipping patent with no publication_number: %r", patent)
            continue

        doc = patent.to_dict()
        doc["updated_at"] = now
        if query_smiles is not None:
            doc["query_smiles"] = query_smiles

        ops.append(
            UpdateOne(
                filter={"publication_number": patent.publication_number},
                update={"$set": doc, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
        )

    if not ops:
        return 0

    result = collection.bulk_write(ops, ordered=False)
    total = result.upserted_count + result.modified_count
    logger.info(
        "save_patents: %d upserted, %d modified (query_smiles=%r)",
        result.upserted_count,
        result.modified_count,
        query_smiles,
    )
    return total


def load_patents(
    *,
    query_smiles: Optional[str] = None,
    limit: int = 0,
) -> List[PatentResult]:
    """Load :class:`PatentResult` objects from MongoDB.

    Args:
        query_smiles: When provided, only returns patents that were saved with
            this SMILES query.  When ``None``, returns all patents.
        limit: Maximum number of documents to return.  ``0`` means no limit.

    Returns:
        List of :class:`PatentResult` objects sorted by similarity score
        descending (nulls last).
    """
    db = get_db()
    coll_name = _get_collection_name(query_smiles)
    collection = db[coll_name]

    query: dict = {}
    if query_smiles is not None:
        query["query_smiles"] = query_smiles

    cursor = collection.find(
        query,
        sort=[("similarity_score", -1)],
        limit=limit,
    )

    results: List[PatentResult] = []
    for doc in cursor:
        results.append(
            PatentResult(
                publication_number=doc.get("publication_number"),
                title=doc.get("title"),
                publication_date=doc.get("publication_date"),
                assignee=doc.get("assignee"),
                abstract=doc.get("abstract"),
                source=doc.get("source", "SureChEMBL"),
                similarity_score=doc.get("similarity_score"),
                document_id=doc.get("document_id"),
            )
        )

    logger.info(
        "load_patents: returned %d record(s) (query_smiles=%r)",
        len(results),
        query_smiles,
    )
    return results


def delete_patents(*, query_smiles: Optional[str] = None) -> int:
    """Delete patent documents from MongoDB.

    Args:
        query_smiles: When provided, deletes only patents tagged with this
            SMILES.  When ``None``, **deletes all patents** — use with care.

    Returns:
        Number of documents deleted.
    """
    db = get_db()
    coll_name = _get_collection_name(query_smiles)
    collection = db[coll_name]

    query: dict = {}
    if query_smiles is not None:
        query["query_smiles"] = query_smiles

    result = collection.delete_many(query)
    logger.info(
        "delete_patents: deleted %d document(s) (query_smiles=%r)",
        result.deleted_count,
        query_smiles,
    )
    return result.deleted_count
