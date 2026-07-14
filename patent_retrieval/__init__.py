"""Resilient, production-ready SureChEMBL patent retrieval pipeline."""

from .batch_fetcher import BatchDocumentFetcher
from .chunk_fetcher import ChunkFetcher
from .config import RetrievalConfig
from .http_session import SureChemblSession
from .progress_tracker import (
    ChunkAttempt,
    RetrievalProgressTracker,
    RetrievalSummary,
)
from .utils import (
    doc_id_for_record,
    extract_documents,
    extract_ids,
    extract_structures,
    first_value_for_keys,
    merge_documents_by_doc_id,
    patent_count,
    response_has_documents,
    values_for_keys,
    walk,
)

__all__ = [
    "BatchDocumentFetcher",
    "ChunkFetcher",
    "ChunkAttempt",
    "RetrievalConfig",
    "RetrievalProgressTracker",
    "RetrievalSummary",
    "SureChemblSession",
    "doc_id_for_record",
    "extract_documents",
    "extract_ids",
    "extract_structures",
    "first_value_for_keys",
    "merge_documents_by_doc_id",
    "patent_count",
    "response_has_documents",
    "values_for_keys",
    "walk",
]
