"""Configuration constants and typed settings for the SureChEMBL retrieval pipeline.

Centralised defaults for connection handling, retries, chunking, and timeouts so
behaviour can be tuned without touching the retrieval logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


DEFAULT_BASE_URL = "https://www.surechembl.org/api"
DEFAULT_SEARCH_TYPE = "similarity"
DEFAULT_MAX_RESULTS = 200
DEFAULT_PAGE_SIZE = 100

DEFAULT_REDUCTION_MAX_PATENTS = 20
DEFAULT_REDUCTION_MIN_SCORE = 55.0

DEFAULT_POLL_SECONDS = 2.0  # kept for backward compatibility

# Polling – exponential backoff
DEFAULT_POLL_INITIAL_WAIT = 1.0    # seconds before the first retry
DEFAULT_POLL_MAX_WAIT = 30.0       # per-interval ceiling
DEFAULT_POLL_TIMEOUT = 300.0       # total wall-clock deadline
DEFAULT_POLL_BACKOFF_FACTOR = 2.0  # each interval is multiplied by this

# Google Patents abstract enrichment
DEFAULT_GOOGLE_PATENTS_TIMEOUT = 10.0  # seconds

# Pipeline output
TOP_PATENTS_LIMIT = 10

# Max chemicals to query individually when resolving to patent IDs
DEFAULT_MAX_CHEMICALS_TO_QUERY = 20

# HTTP settings
DEFAULT_CONNECTION_TIMEOUT = 10.0
DEFAULT_READ_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 1.0  # exponential backoff multiplier (0.5, 1, 2, 4...)
DEFAULT_RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
DEFAULT_RETRY_ALLOWED_METHODS = frozenset({"HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS"})

DEFAULT_CHUNK_RETRIES = 1

# Batch document settings
DEFAULT_BATCH_CHUNK_SIZE = 40
DEFAULT_MIN_BATCH_CHUNK_SIZE = 1


@dataclass(frozen=True)
class RetrievalConfig:
    """Immutable configuration for the SureChEMBL retrieval pipeline."""

    base_url: str = DEFAULT_BASE_URL
    search_type: str = DEFAULT_SEARCH_TYPE
    max_results: int = DEFAULT_MAX_RESULTS
    page_size: int = DEFAULT_PAGE_SIZE
    poll_seconds: float = DEFAULT_POLL_SECONDS

    poll_initial_wait: float = DEFAULT_POLL_INITIAL_WAIT
    poll_max_wait: float = DEFAULT_POLL_MAX_WAIT
    poll_timeout: float = DEFAULT_POLL_TIMEOUT
    poll_backoff_factor: float = DEFAULT_POLL_BACKOFF_FACTOR

    google_patents_timeout: float = DEFAULT_GOOGLE_PATENTS_TIMEOUT
    max_chemicals_to_query: int = DEFAULT_MAX_CHEMICALS_TO_QUERY

    connection_timeout: float = DEFAULT_CONNECTION_TIMEOUT
    read_timeout: float = DEFAULT_READ_TIMEOUT
    timeout: Tuple[float, float] = (
        DEFAULT_CONNECTION_TIMEOUT,
        DEFAULT_READ_TIMEOUT,
    )

    max_retries: int = DEFAULT_MAX_RETRIES
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR
    retry_status_codes: frozenset = DEFAULT_RETRY_STATUS_CODES
    retry_allowed_methods: frozenset = DEFAULT_RETRY_ALLOWED_METHODS

    batch_chunk_size: int = DEFAULT_BATCH_CHUNK_SIZE
    chunk_retries: int = DEFAULT_CHUNK_RETRIES

    reduction_max_patents: int = DEFAULT_REDUCTION_MAX_PATENTS
    reduction_min_score: float = DEFAULT_REDUCTION_MIN_SCORE

    def __post_init__(self) -> None:
        if self.batch_chunk_size < DEFAULT_MIN_BATCH_CHUNK_SIZE:
            raise ValueError(
                f"batch_chunk_size must be at least {DEFAULT_MIN_BATCH_CHUNK_SIZE}"
            )
        if self.max_results < 1:
            raise ValueError("max_results must be at least 1")
        if self.page_size < 1:
            raise ValueError("page_size must be at least 1")
        if self.poll_initial_wait <= 0:
            raise ValueError("poll_initial_wait must be positive")
        if self.poll_max_wait < self.poll_initial_wait:
            raise ValueError("poll_max_wait must be >= poll_initial_wait")
        if self.poll_timeout <= 0:
            raise ValueError("poll_timeout must be positive")
        if self.poll_backoff_factor < 1.0:
            raise ValueError("poll_backoff_factor must be >= 1.0")
        if self.max_chemicals_to_query < 1:
            raise ValueError("max_chemicals_to_query must be at least 1")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.chunk_retries < 0:
            raise ValueError("chunk_retries must be non-negative")

    @classmethod
    def default(cls) -> "RetrievalConfig":
        return cls()
