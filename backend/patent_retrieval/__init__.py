"""Resilient, production-ready SureChEMBL patent retrieval pipeline."""

from .core import (
    PatentRetrievalPipeline,
    RetrievalConfig,
    SureChemblSession,
    TOP_PATENTS_LIMIT,
)
from .database import (
    close_client,
    delete_patents,
    get_client,
    get_db,
    load_patents,
    save_patents,
)
from .models import (
    ChemicalMatch,
    ChunkAttempt,
    PatentResult,
    RetrievalError,
    RetrievalProgressTracker,
    RetrievalSummary,
)
from .services import (
    BatchDocumentFetcher,
    ChunkFetcher,
    enrich_missing_abstracts,
    enrich_patent,
    extract_batch_patents,
    fetch_patent_details,
    poll_until_complete,
    retrieve_patent_ids_for_chemicals,
    retrieve_search_results,
    start_similarity_search,
    validate_smiles,
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
    # Pipeline entry point
    "PatentRetrievalPipeline",
    # MongoDB helpers
    "get_db",
    "get_client",
    "close_client",
    "save_patents",
    "load_patents",
    "delete_patents",
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
