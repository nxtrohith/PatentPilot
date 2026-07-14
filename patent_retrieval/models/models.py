"""Core data models for the patent retrieval pipeline.

These types are shared across all service layers and the pipeline itself.
No business logic lives here — only data definitions and a domain exception.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class RetrievalError(Exception):
    """Raised when the retrieval pipeline encounters an unrecoverable error.

    Wraps API failures, unexpected response shapes, and other conditions that
    prevent the pipeline from producing a result.
    """


@dataclass(frozen=True)
class ChemicalMatch:
    """A chemical compound returned by a SureChEMBL similarity search.

    Attributes:
        chemical_id: SureChEMBL identifier for the compound.
        similarity_score: Tanimoto (or equivalent) score in [0, 1], or None
            when the API does not return a score.
    """

    chemical_id: str
    similarity_score: Optional[float] = None


@dataclass
class PatentResult:
    """A patent with enriched metadata, ready for downstream consumption.

    All string fields are ``None`` when the information could not be found —
    never empty strings, to make downstream null-checks unambiguous.

    Attributes:
        publication_number: Canonical patent number (e.g. ``"US-12345-A1"``).
        title: Invention title.
        publication_date: ISO-like date string (e.g. ``"20240101"``).
        assignee: Semicolon-separated list of assignees/applicants.
        abstract: Full abstract text.
        source: Data source, either ``"SureChEMBL"`` or ``"Google Patents"``.
        similarity_score: Tanimoto score of the most-similar chemical that
            links this patent to the query compound.
        document_id: SureChEMBL internal document identifier.
    """

    publication_number: Optional[str] = None
    title: Optional[str] = None
    publication_date: Optional[str] = None
    assignee: Optional[str] = None
    abstract: Optional[str] = None
    source: str = "SureChEMBL"
    similarity_score: Optional[float] = None
    document_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dict suitable for JSON serialisation."""
        return {
            "publication_number": self.publication_number,
            "title": self.title,
            "publication_date": self.publication_date,
            "assignee": self.assignee,
            "abstract": self.abstract,
            "source": self.source,
            "similarity_score": self.similarity_score,
            "document_id": self.document_id,
        }
