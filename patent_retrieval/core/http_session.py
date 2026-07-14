"""Reusable SureChEMBL HTTP session with retries and timeouts.

Provides a :class:`requests.Session` configured with automatic retries for
connection errors, timeouts, and transient HTTP status codes.  Every outgoing
request receives a configured connection/read timeout.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import RetrievalConfig

logger = logging.getLogger(__name__)


def build_retry_strategy(config: RetrievalConfig) -> Retry:
    """Build a urllib3 Retry strategy from retrieval configuration."""
    return Retry(
        total=config.max_retries,
        backoff_factor=config.backoff_factor,
        status_forcelist=config.retry_status_codes,
        allowed_methods=config.retry_allowed_methods,
        raise_on_status=False,
        # ConnectionError and RemoteDisconnected are retried via connect
        # retries, Timeout via read/connect retries.
    )


def create_session(config: RetrievalConfig) -> requests.Session:
    """Return a new requests.Session configured for resilient retrieval."""
    session = requests.Session()
    retry_strategy = build_retry_strategy(config)
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class SureChemblSession:
    """Thin wrapper around a configured requests.Session.

    Guarantees that every request is made with the configured timeouts and
    logs retries/attempts at debug level.
    """

    def __init__(self, config: Optional[RetrievalConfig] = None) -> None:
        self.config = config or RetrievalConfig.default()
        self._session = create_session(self.config)

    @property
    def session(self) -> requests.Session:
        return self._session

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Any] = None,
        json: Optional[Any] = None,
        timeout: Optional[tuple] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Make a request with the configured timeout and retry policy."""
        request_timeout = timeout or self.config.timeout
        logger.debug("%s %s (timeout=%s)", method, url, request_timeout)
        response = self._session.request(
            method,
            url,
            params=params,
            json=json,
            timeout=request_timeout,
            **kwargs,
        )
        return response

    def json_request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Any] = None,
        json: Optional[Any] = None,
        timeout: Optional[tuple] = None,
        **kwargs: Any,
    ) -> Any:
        """Make a request and return parsed JSON, raising on HTTP errors."""
        response = self.request(
            method, url, params=params, json=json, timeout=timeout, **kwargs
        )
        response.raise_for_status()
        return response.json()

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "SureChemblSession":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
