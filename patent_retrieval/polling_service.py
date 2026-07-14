"""Poll a SureChEMBL search until it finishes, fails, or times out.

Uses exponential backoff so the server is not hammered during long-running
searches.  The initial wait, per-interval cap, multiplier, and overall
deadline are all drawn from :class:`RetrievalConfig`.

The poll interval sequence is:
    poll_initial_wait, poll_initial_wait * factor, ..., poll_max_wait, poll_max_wait, ...

The total wall-clock time is bounded by ``config.poll_timeout``.
"""
from __future__ import annotations

import logging
import time

import requests

from .config import RetrievalConfig
from .http_session import SureChemblSession
from .models import RetrievalError
from .utils import values_for_keys

logger = logging.getLogger(__name__)

_COMPLETE_WORDS = frozenset({"finished", "complete", "completed", "done"})
_FAILURE_WORDS  = frozenset({"failed", "error"})


def poll_until_complete(
    session: SureChemblSession,
    config: RetrievalConfig,
    search_hash: str,
) -> None:
    """Block until the search completes, raising on failure or timeout.

    Args:
        session: Configured, retry-enabled HTTP session.
        config: Pipeline configuration.  Uses ``poll_initial_wait``,
            ``poll_max_wait``, ``poll_backoff_factor``, ``poll_timeout``,
            ``connection_timeout``.
        search_hash: Hash returned by :func:`search_service.start_similarity_search`.

    Raises:
        RetrievalError: When SureChEMBL reports that the search failed.
        TimeoutError: When the configured deadline is reached.
        requests.RequestException: On unrecoverable network errors that exhaust
            all remaining poll attempts before the deadline.
    """
    endpoint = f"{config.base_url}/search/{search_hash}/status"
    deadline  = time.monotonic() + config.poll_timeout
    wait      = config.poll_initial_wait
    attempt   = 0

    logger.info(
        "Polling hash=%s  timeout=%.0fs  initial_wait=%.1fs  max_wait=%.1fs  factor=%.1f",
        search_hash,
        config.poll_timeout,
        config.poll_initial_wait,
        config.poll_max_wait,
        config.poll_backoff_factor,
    )

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                f"Polling timed out after {config.poll_timeout:.0f}s "
                f"for search hash {search_hash!r}."
            )

        attempt += 1
        logger.debug(
            "Poll attempt %d  hash=%s  remaining=%.1fs",
            attempt, search_hash, remaining,
        )

        response = None
        try:
            response = session.json_request(
                "GET",
                endpoint,
                timeout=(config.connection_timeout, 30.0),
            )
        except requests.RequestException as exc:
            # Transient network error — log and fall through to the backoff sleep.
            logger.warning(
                "Poll attempt %d failed (network): %s. "
                "Will retry if time remains.",
                attempt, exc,
            )

        if response is not None:
            status_words = [
                v.lower()
                for v in values_for_keys(response, {"status", "message"})
            ]
            joined = " ".join(status_words)

            if any(w in joined for w in _FAILURE_WORDS):
                raise RetrievalError(
                    f"SureChEMBL reported search failure: {joined!r}"
                )

            if any(w in joined for w in _COMPLETE_WORDS):
                logger.info(
                    "Search complete after %d poll attempt(s). Status: %r",
                    attempt, joined.strip() or "(no text)",
                )
                return

            # Older API versions signal completion by emitting a resultCount
            # field rather than a terminal status string.
            if values_for_keys(response, {"resultcount"}):
                logger.info(
                    "Search complete after %d attempt(s) (resultCount present).",
                    attempt,
                )
                return

            logger.debug("Search still running. Status: %r", joined.strip())

        # ------------------------------------------------------------------ #
        # Backoff: sleep for at most (remaining - small_buffer) seconds.      #
        # ------------------------------------------------------------------ #
        remaining_after = deadline - time.monotonic()
        sleep_time = min(wait, remaining_after - 0.05)
        if sleep_time <= 0:
            raise TimeoutError(
                f"Polling timed out after {config.poll_timeout:.0f}s "
                f"for search hash {search_hash!r}."
            )

        logger.debug(
            "Sleeping %.1fs before poll attempt %d (next wait cap: %.1fs).",
            sleep_time, attempt + 1,
            min(wait * config.poll_backoff_factor, config.poll_max_wait),
        )
        time.sleep(sleep_time)

        # Advance the backoff, capped at poll_max_wait.
        wait = min(wait * config.poll_backoff_factor, config.poll_max_wait)
