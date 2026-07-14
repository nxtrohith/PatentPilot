"""Resilient, production-ready SureChEMBL patent retrieval pipeline."""

from .batch_fetcher import BatchDocumentFetcher
from .chunk_fetcher import ChunkFetcher
from .config import RetrievalConfig, TOP_PATENTS_LIMIT
from .enrichment_service import enrich_missing_abstracts
from .http_session import SureChemblSession
from .metadata_service import fetch_patent_details, retrieve_patent_ids_for_chemicals
from .models import ChemicalMatch, PatentResult, RetrievalError
from .patent_enrichment import enrich_patent, extract_batch_patents
from .pipeline import PatentRetrievalPipeline
from .polling_service import poll_until_complete
from .progress_tracker import (
    ChunkAttempt,
    RetrievalProgressTracker,
    RetrievalSummary,
)
from .results_service import retrieve_search_results
from .search_service import start_similarity_search, validate_smiles
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
    # Pipeline entry point
    "PatentRetrievalPipeline",
    # Data models
    "ChemicalMatch",
    "PatentResult",
    "RetrievalError",
    # Service functions
    "validate_smiles",
    "start_similarity_search",
    "poll_until_complete",
    "retrieve_search_results",
    "retrieve_patent_ids_for_chemicals",
    "fetch_patent_details",
    "enrich_missing_abstracts",
    # Configuration
    "RetrievalConfig",
    "TOP_PATENTS_LIMIT",
    # Low-level building blocks
    "BatchDocumentFetcher",
    "ChunkFetcher",
    "ChunkAttempt",
    "RetrievalProgressTracker",
    "RetrievalSummary",
    "SureChemblSession",
    "enrich_patent",
    "extract_batch_patents",
    # Utilities
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
