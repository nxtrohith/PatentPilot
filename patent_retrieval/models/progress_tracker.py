"""Structured progress logging for the retrieval pipeline.

Tracks and emits chunk number, request URL, retry attempts, execution time,
and success/failure for each retrieval operation.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievalSummary:
    """Summary of a batched retrieval operation."""

    requested_ids: int = 0
    retrieved_ids: int = 0
    failed_ids: int = 0
    failed_id_list: List[str] = field(default_factory=list)
    chunks_total: int = 0
    chunks_successful: int = 0
    chunks_failed: int = 0
    total_duration_seconds: float = 0.0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "requested_ids": self.requested_ids,
            "retrieved_ids": self.retrieved_ids,
            "failed_ids": self.failed_ids,
            "failed_id_list": self.failed_id_list,
            "chunks_total": self.chunks_total,
            "chunks_successful": self.chunks_successful,
            "chunks_failed": self.chunks_failed,
            "total_duration_seconds": round(self.total_duration_seconds, 3),
        }


@dataclass(frozen=True)
class ChunkAttempt:
    """Result of one chunk fetch attempt."""

    chunk_index: int
    chunk_size: int
    url: str
    method: str
    success: bool
    duration_seconds: float
    retry_count: int = 0
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "chunk_index": self.chunk_index,
            "chunk_size": self.chunk_size,
            "url": self.url,
            "method": self.method,
            "success": self.success,
            "duration_seconds": round(self.duration_seconds, 3),
            "retry_count": self.retry_count,
            "error": self.error,
        }


class ChunkContext:
    """Mutable state for a single chunk request."""

    def __init__(
        self,
        chunk_index: int,
        chunk_size: int,
        url: str,
        method: str,
    ) -> None:
        self.chunk_index = chunk_index
        self.chunk_size = chunk_size
        self.url = url
        self.method = method
        self.retry_count = 0
        self.success = False
        self.error_message: Optional[str] = None
        self._chunk_start: Optional[float] = None
        self.duration_seconds = 0.0

    def start(self) -> None:
        self._chunk_start = time.monotonic()

    def stop(self) -> None:
        if self._chunk_start is not None:
            self.duration_seconds = time.monotonic() - self._chunk_start

    def record_retry(self) -> None:
        self.retry_count += 1
        logger.info(
            "Chunk %d retry attempt %d for %s",
            self.chunk_index,
            self.retry_count,
            self.url,
        )

    def set_success(self) -> None:
        self.success = True
        self.error_message = None

    def set_failure(self, message: str) -> None:
        self.success = False
        self.error_message = message

    def to_attempt(self) -> ChunkAttempt:
        return ChunkAttempt(
            chunk_index=self.chunk_index,
            chunk_size=self.chunk_size,
            url=self.url,
            method=self.method,
            success=self.success,
            duration_seconds=self.duration_seconds,
            retry_count=self.retry_count,
            error=self.error_message,
        )


class RetrievalProgressTracker:
    """Tracks and logs per-chunk progress and final summary."""

    def __init__(self) -> None:
        self._start_time: Optional[float] = None
        self._chunks: List[ChunkAttempt] = []
        self._failed_ids: List[str] = []

    def start(self) -> None:
        self._start_time = time.monotonic()

    @contextmanager
    def track_chunk(
        self,
        chunk_index: int,
        chunk_size: int,
        url: str,
        method: str,
    ) -> Iterator[ChunkContext]:
        """Context manager to time and log a single chunk request."""
        ctx = ChunkContext(chunk_index, chunk_size, url, method)
        ctx.start()
        logger.info(
            "Chunk %d: %s %s (size=%d)",
            chunk_index,
            method,
            url,
            chunk_size,
        )
        try:
            yield ctx
        finally:
            ctx.stop()
            self._chunks.append(ctx.to_attempt())
            status = "success" if ctx.success else "failure"
            logger.info(
                "Chunk %d finished in %.3fs: %s (retries=%d)",
                chunk_index,
                ctx.duration_seconds,
                status,
                ctx.retry_count,
            )
            if ctx.error_message:
                logger.warning("Chunk %d error: %s", chunk_index, ctx.error_message)

    def record_failed_ids(self, ids: List[str]) -> None:
        self._failed_ids.extend(ids)

    def summary(self, requested_ids: int, total_chunks: int) -> RetrievalSummary:
        if self._start_time is None:
            duration = 0.0
        else:
            duration = time.monotonic() - self._start_time

        successful = sum(1 for c in self._chunks if c.success)
        failed = sum(1 for c in self._chunks if not c.success)
        retrieved_ids = requested_ids - len(self._failed_ids)

        return RetrievalSummary(
            requested_ids=requested_ids,
            retrieved_ids=retrieved_ids,
            failed_ids=len(self._failed_ids),
            failed_id_list=self._failed_ids[:],
            chunks_total=total_chunks,
            chunks_successful=successful,
            chunks_failed=failed,
            total_duration_seconds=duration,
        )

    def log_summary(self, summary: RetrievalSummary) -> None:
        logger.info("Retrieval summary: %s", summary.as_dict())
