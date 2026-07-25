"""Batch fetcher for /document/batch with chunking and failure isolation.

Splits a large list of patent IDs into configurable chunks, fetches each chunk
through :class:`ChunkFetcher`, merges successful responses, and continues even
when individual chunks fail.  Temporary chunk responses are discarded after
extraction to keep memory usage bounded.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .chunk_fetcher import ChunkFetcher
from .patent_enrichment import extract_batch_patents
from ..core import RetrievalConfig, SureChemblSession
from ..models import RetrievalProgressTracker
from ..utils import extract_documents, merge_documents_by_doc_id

logger = logging.getLogger(__name__)


class BatchDocumentFetcher:
    """Fetches patent details in chunks from the document batch endpoint."""

    def __init__(
        self,
        session: SureChemblSession,
        config: RetrievalConfig,
        tracker: Optional[RetrievalProgressTracker] = None,
    ) -> None:
        self.session = session
        self.config = config
        self.tracker = tracker or RetrievalProgressTracker()
        self.chunk_fetcher = ChunkFetcher(session, config, self.tracker)

    def fetch(
        self,
        patent_ids: List[str],
        base_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch details for ``patent_ids`` in chunks and return merged docs.

        Failed chunk IDs are recorded in the tracker summary but do not abort the
        rest of the batch.
        """
        base_url = base_url or self.config.base_url
        if not patent_ids:
            self.tracker.start()
            summary = self.tracker.summary(requested_ids=0, total_chunks=0)
            self.tracker.log_summary(summary)
            return {"data": {"results": {"documents": []}}}

        self.tracker.start()
        chunk_size = self.config.batch_chunk_size
        chunks = self._chunk_ids(patent_ids, chunk_size)
        total_chunks = len(chunks)

        all_documents: List[Dict[str, Any]] = []
        for index, chunk_ids in enumerate(chunks, start=1):
            chunk_data = self.chunk_fetcher.fetch_chunk(
                chunk_index=index,
                patent_ids=chunk_ids,
                base_url=base_url,
            )
            if chunk_data is not None:
                # /document/batch returns data as a list of nested patent
                # objects, so enrich it before exposing it to downstream code.
                chunk_documents = extract_batch_patents(chunk_data)
                # Retain compatibility with the older documented/results shape
                # used by existing callers and test fixtures; deployed batch
                # responses take the nested data-list branch above.
                if not chunk_documents:
                    chunk_documents = extract_documents(chunk_data)
                if chunk_documents:
                    all_documents = merge_documents_by_doc_id(
                        all_documents,
                        chunk_documents,
                    )
                logger.info(
                    "Chunk %d/%d: merged %d documents (running total: %d)",
                    index,
                    total_chunks,
                    len(chunk_documents),
                    len(all_documents),
                )
            # Explicitly discard the chunk response and its parsed JSON.
            del chunk_data

        summary = self.tracker.summary(
            requested_ids=len(patent_ids),
            total_chunks=total_chunks,
        )
        self.tracker.log_summary(summary)

        return {
            "data": {
                "results": {
                    "documents": all_documents,
                    "retrieval_summary": summary.as_dict(),
                }
            }
        }

    @staticmethod
    def _chunk_ids(ids: List[str], chunk_size: int) -> List[List[str]]:
        """Split IDs into contiguous chunks of size ``chunk_size``."""
        return [ids[i : i + chunk_size] for i in range(0, len(ids), chunk_size)]
