"""Low-level chunk fetcher with retry-until-failure resilience.

Fetches a single chunk of patent IDs from ``/document/batch``, leverages the
shared retry-enabled session for automatic retries, and records manual retries
and final failure without aborting the overall workflow.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from .config import RetrievalConfig
from .http_session import SureChemblSession
from .progress_tracker import ChunkContext, RetrievalProgressTracker

logger = logging.getLogger(__name__)


class ChunkFetcher:
    """Fetches one chunk of patent IDs from the document batch endpoint."""

    def __init__(
        self,
        session: SureChemblSession,
        config: RetrievalConfig,
        tracker: RetrievalProgressTracker,
    ) -> None:
        self.session = session
        self.config = config
        self.tracker = tracker

    def fetch_chunk(
        self,
        chunk_index: int,
        patent_ids: List[str],
        base_url: str,
    ) -> Optional[Dict[str, Any]]:
        """Fetch one chunk; return None if the chunk ultimately fails.

        The session already performs automatic retries.  This method performs an
        additional manual retry at the chunk level so callers can inspect and log
        the final failure without aborting the larger batch.
        """
        endpoint = f"{base_url}/document/batch"
        params = {"doc_ids": ",".join(patent_ids)}
        max_attempts = self.config.chunk_retries + 1

        for attempt in range(max_attempts):
            with self.tracker.track_chunk(
                chunk_index=chunk_index,
                chunk_size=len(patent_ids),
                url=endpoint,
                method="POST",
            ) as ctx:
                try:
                    response = self.session.request(
                        "POST",
                        endpoint,
                        params=params,
                        timeout=self.config.timeout,
                    )
                    response.raise_for_status()
                    data = response.json()
                    self._save_raw_batch_response(response.content)
                    ctx.set_success()
                    logger.info(
                        "Chunk %d: fetched %d patent IDs from %s",
                        chunk_index,
                        len(patent_ids),
                        response.request.url,
                    )
                    return data
                except (requests.RequestException, ValueError) as exc:
                    ctx.set_failure(str(exc))
                    if attempt == 0 and ctx.retry_count == 0:
                        # urllib3 may have already retried, but we count only
                        # manual retries explicitly.  record_retry is used for
                        # additional manual attempts beyond the first.
                        pass
                    if attempt < max_attempts - 1:
                        ctx.record_retry()
                        logger.warning(
                            "Chunk %d failed on attempt %d/%d: %s",
                            chunk_index,
                            attempt + 1,
                            max_attempts,
                            exc,
                        )
                    else:
                        logger.error(
                            "Chunk %d failed after %d attempts; skipping %d IDs: %s",
                            chunk_index,
                            max_attempts,
                            len(patent_ids),
                            exc,
                        )
                        self.tracker.record_failed_ids(patent_ids)

        return None

    @staticmethod
    def _save_raw_batch_response(raw_response: bytes) -> None:
        """Persist the unmodified API bytes for schema debugging.

        For a chunked batch, the file is overwritten by each successful request;
        it therefore always contains one complete, exact API response rather
        than a synthesized/merged representation.
        """
        if not isinstance(raw_response, bytes):
            logger.warning(
                "Could not save raw /document/batch response because response.content is %s.",
                type(raw_response).__name__,
            )
            return
        path = Path(__file__).resolve().parents[1] / "logs" / "debug_document_batch_response.json"
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(raw_response)
        logger.info("Saved unmodified /document/batch response to %s", path)
