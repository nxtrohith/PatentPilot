"""Normalized data model for patents flowing through the reduction pipeline.

SureChEMBL's raw JSON shape is loosely specified (see ``patents_retreival.py``),
so :meth:`PatentRecord.from_raw` is deliberately defensive: it accepts several
plausible key spellings per field and always produces a usable record instead
of raising on missing/odd data.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Alternate key spellings tolerated per logical field, mirroring the
# flexible lookups already used in patents_retreival.py.
_FIELD_ALIASES: Dict[str, List[str]] = {
    "doc_id": ["doc_id", "docid", "document_id", "documentid", "patent_id", "patentid", "id"],
    "family": ["family", "family_id", "familyid", "patent_family", "docdb_family_id"],
    "title": ["title", "documenttitle", "patenttitle"],
    "abstract": ["abstract"],
    "claims": ["claims", "claim", "independent_claims", "independentclaims"],
    "description": ["description", "desc", "full_text", "fulltext"],
    "legal_status": ["legal_status", "legalstatus", "status", "legal_event", "legalevent"],
    "publication_date": [
        "publication_date",
        "publicationdate",
        "pubdate",
        "pub_date",
        "date",
    ],
    "matched_chemicals": ["matched_chemicals", "matchedchemicals", "chemicals"],
    "annotations": ["annotations", "chemical_annotations", "chemicalannotations"],
    "chemical_ids": ["chemical_ids", "chemicalids", "chem_ids"],
    "similarity": ["similarity", "similarity_score", "score", "structure_similarity"],
    "country_code": ["country_code", "countrycode", "country"],
    "publication_number": [
        "publication_number",
        "publicationnumber",
        "publication_no",
        "publicationno",
    ],
}

_DATE_FORMATS = ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d", "%d-%m-%Y")


def _first_present(raw: Dict[str, Any], keys: List[str]) -> Any:
    lowered = {str(k).lower(): v for k, v in raw.items()}
    for key in keys:
        if key in lowered and lowered[key] is not None:
            return lowered[key]
    return None


def _coerce_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (str, int, float)):
        return [value]
    if isinstance(value, dict):
        return list(value.values())
    return []


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(_coerce_text(v) for v in value)
    if isinstance(value, dict):
        return " ".join(_coerce_text(v) for v in value.values())
    return str(value)


def _parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    if not text:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    match = re.match(r"^(\d{4})", text)
    if match:
        try:
            return date(int(match.group(1)), 1, 1)
        except ValueError:
            return None
    logger.debug("Could not parse publication date: %r", value)
    return None


def _parse_similarity(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        similarity = float(value)
    except (TypeError, ValueError):
        return None
    # Tolerate similarity already expressed as a 0-100 percentage.
    if similarity > 1.0:
        similarity = similarity / 100.0
    return max(0.0, min(1.0, similarity))


def _extract_country_code(doc_id: str, publication_number: str, explicit: Any) -> Optional[str]:
    if explicit:
        text = str(explicit).strip().upper()
        if len(text) == 2 and text.isalpha():
            return text
    for candidate in (doc_id, publication_number):
        if not candidate:
            continue
        match = re.match(r"^([A-Za-z]{2})", str(candidate).strip())
        if match:
            return match.group(1).upper()
    return None


@dataclass
class PatentRecord:
    """A normalized view over one raw SureChEMBL patent object."""

    doc_id: str
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    family_id: Optional[str] = None
    country_code: Optional[str] = None
    publication_number: Optional[str] = None
    publication_date: Optional[date] = None

    title: str = ""
    abstract: str = ""
    claims: str = ""
    description: str = ""

    legal_status: str = ""

    matched_chemicals: List[Any] = field(default_factory=list)
    annotations: List[Any] = field(default_factory=list)
    chemical_ids: List[Any] = field(default_factory=list)
    similarity: Optional[float] = None

    # Populated by the family reducer for the chosen representative.
    family_members: List["PatentRecord"] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> "PatentRecord":
        if not isinstance(raw, dict):
            raise TypeError(f"Expected a dict-like patent object, got {type(raw)!r}")

        doc_id = _first_present(raw, _FIELD_ALIASES["doc_id"])
        if doc_id is None:
            # Fall back to publication number, then a stable repr, so the
            # pipeline never crashes on an unusual payload.
            doc_id = _first_present(raw, _FIELD_ALIASES["publication_number"])
        if doc_id is None:
            doc_id = f"unknown:{id(raw)}"
            logger.warning("Patent object missing doc_id; assigned placeholder %s", doc_id)
        doc_id = str(doc_id)

        publication_number = _first_present(raw, _FIELD_ALIASES["publication_number"])
        publication_number = str(publication_number) if publication_number else None

        family_raw = _first_present(raw, _FIELD_ALIASES["family"])
        family_id = str(family_raw) if family_raw is not None else None

        country_code = _extract_country_code(
            doc_id,
            publication_number or "",
            _first_present(raw, _FIELD_ALIASES["country_code"]),
        )

        return cls(
            doc_id=doc_id,
            raw=raw,
            family_id=family_id,
            country_code=country_code,
            publication_number=publication_number,
            publication_date=_parse_date(_first_present(raw, _FIELD_ALIASES["publication_date"])),
            title=_coerce_text(_first_present(raw, _FIELD_ALIASES["title"])),
            abstract=_coerce_text(_first_present(raw, _FIELD_ALIASES["abstract"])),
            claims=_coerce_text(_first_present(raw, _FIELD_ALIASES["claims"])),
            description=_coerce_text(_first_present(raw, _FIELD_ALIASES["description"])),
            legal_status=_coerce_text(_first_present(raw, _FIELD_ALIASES["legal_status"])),
            matched_chemicals=_coerce_list(_first_present(raw, _FIELD_ALIASES["matched_chemicals"])),
            annotations=_coerce_list(_first_present(raw, _FIELD_ALIASES["annotations"])),
            chemical_ids=_coerce_list(_first_present(raw, _FIELD_ALIASES["chemical_ids"])),
            similarity=_parse_similarity(_first_present(raw, _FIELD_ALIASES["similarity"])),
        )

    @property
    def family_key(self) -> str:
        """Grouping key for family collapse: family id if known, else self."""
        return self.family_id if self.family_id else f"__no_family__:{self.doc_id}"


@dataclass
class ScoreBreakdown:
    """All individually-computed scores plus the final composite."""

    structure: float = 0.0
    chemical_evidence: float = 0.0
    claim_importance: float = 0.0
    legal: float = 0.0
    recency: float = 0.0
    final: float = 0.0

    def as_dict(self) -> Dict[str, float]:
        return {
            "structure": round(self.structure, 2),
            "chemicalEvidence": round(self.chemical_evidence, 2),
            "claimImportance": round(self.claim_importance, 2),
            "legal": round(self.legal, 2),
            "recency": round(self.recency, 2),
            "final": round(self.final, 2),
        }


@dataclass
class RankedPatent:
    """One ranked, filtered output row: representative + its family + scores."""

    representative: PatentRecord
    family_members: List[PatentRecord]
    scores: ScoreBreakdown
    rank: int

    def as_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.representative.doc_id,
            "representative": self.representative,
            "family_members": self.family_members,
            "scores": self.scores.as_dict(),
            "rank": self.rank,
        }


@dataclass
class PipelineStatistics:
    """Funnel counts recorded at each stage of the pipeline."""

    initial_patents: int = 0
    after_duplicate_removal: int = 0
    after_family_collapse: int = 0
    after_score_filtering: int = 0
    final_patents: int = 0

    def as_dict(self) -> Dict[str, int]:
        return {
            "initial_patents": self.initial_patents,
            "after_duplicate_removal": self.after_duplicate_removal,
            "after_family_collapse": self.after_family_collapse,
            "after_score_filtering": self.after_score_filtering,
            "final_patents": self.final_patents,
        }


@dataclass
class ReductionResult:
    """Final output of :class:`PatentReductionPipeline.run`."""

    reduced_patents: List[RankedPatent]
    statistics: PipelineStatistics
