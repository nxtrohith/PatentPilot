"""MongoDB connection management for PatentPilot.

Provides a lazy singleton client and a helper to access the default database.
The MONGODB_URI is read from the environment (populated from .env via
python-dotenv).  Import ``get_db`` wherever you need a database handle.

Example::

    from patent_retrieval.db import get_db

    db = get_db()
    db.patents.insert_one({"publication_number": "US-12345-A1"})
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

load_dotenv()  # reads .env into os.environ if not already set

logger = logging.getLogger(__name__)

_client: Optional[MongoClient] = None  # module-level singleton

DEFAULT_DB_NAME = "patentpilot"


def get_client() -> MongoClient:
    """Return the shared MongoClient, creating it on first call.

    The client is intentionally reused across calls to avoid opening a new
    connection pool for every request.

    Raises:
        RuntimeError: If ``MONGODB_URI`` is not set in the environment.
    """
    global _client
    if _client is None:
        uri = os.getenv("MONGODB_URI")
        if not uri:
            raise RuntimeError(
                "MONGODB_URI is not set. "
                "Add it to your .env file or export it before running."
            )
        _client = MongoClient(uri)
        logger.debug("MongoDB client created for host(s): %s", _client.topology_description)
    return _client


def get_db(name: str = DEFAULT_DB_NAME) -> Database:
    """Return the named MongoDB database using the shared client.

    Args:
        name: Database name (default: ``"patentpilot"``).

    Returns:
        A :class:`pymongo.database.Database` handle.
    """
    return get_client()[name]


def close_client() -> None:
    """Close the shared MongoClient and reset the singleton.

    Call this on application shutdown to cleanly release connection-pool
    resources.  Safe to call even if the client was never initialised.
    """
    global _client
    if _client is not None:
        _client.close()
        _client = None
        logger.debug("MongoDB client closed.")
