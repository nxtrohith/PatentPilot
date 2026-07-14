"""Defensive parser for nested SureChEMBL ``/document/batch`` responses.

The published OpenAPI schema deliberately leaves ``data`` untyped.  The deployed
endpoint returns ``data`` as a list of nested patent objects, not as
``data.results.documents``.  This module converts that response into the flat
metadata contract already consumed by downstream code, without changing the
reduction, scoring, or ranking layers.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# This is both executable documentation and the schema comparison required for
# troubleshooting deployed SureChEMBL responses.
FIELD_PATHS: Tuple[Tuple[str, str, str], ...] = (
    ("doc_id", "doc_id | docId | document_id", "data[i].doc_id",),
    (
        "title",
        "title | documentTitle | patentTitle",
        "data[i].contents.patentDocument.bibliographicData.technicalData.inventionTitles[*].title",
    ),
    (
        "publication number",
        "publication_number | publicationNumber | publication_no | publicationNo",
        "data[i].contents.patentDocument.bibliographicData.publicationReference[0].ucid (preferred); documentId[0].country.content + docNumber + kind (fallback)",
    ),
    (
        "publication date",
        "publication_date | publicationDate | pubdate | pub_date | date",
        "data[i].contents.patentDocument.bibliographicData.publicationReference[0].documentId[0].date",
    ),
    (
        "assignee",
        "assignee | applicant",
        "data[i].contents.patentDocument.bibliographicData.parties[0].assignees.assignee[*].addressbook.name (applicant lastName/name fallback)",
    ),
    (
        "abstract",
        "abstract",
        "data[i].contents.patentDocument.abstracts[*].section.content",
    ),
    (
        "claims",
        "claims | claim | independent_claims | independentClaims",
        "data[i].contents.patentDocument.claimResponses[*].section.content",
    ),
    (
        "description",
        "description | desc | full_text | fullText",
        "data[i].contents.patentDocument.descriptions[*].section.content",
    ),
    (
        "legal status",
        "legal_status | legalStatus | status | legal_event | legalEvent",
        "data[i].contents.patentDocument.legalStatus[*]['legal-event'][*] (event-title.$, @code, @date, @impact)",
    ),
    (
        "patent family",
        "family | family_id | familyId | patent_family | docdb_family_id",
        "data[i].contents.patentDocument.family[0]",
    ),
)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _path(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def _preferred_text(items: Iterable[Any], value_path: Sequence[str]) -> str:
    """Select English text when available, otherwise the first non-empty text."""
    candidates: List[Tuple[str, str]] = []
    for item in items:
        candidate = item
        for key in value_path:
            candidate = _path(candidate, key)
        text = _text(candidate)
        if text:
            candidates.append((_text(_path(item, "lang")).upper(), text))
    for language, text in candidates:
        if language == "EN":
            return text
    return candidates[0][1] if candidates else ""


def _join_sections(items: Any) -> str:
    values: List[str] = []
    for item in _list(items):
        content = _text(_path(item, "section", "content"))
        if content:
            values.append(content)
    return "\n\n".join(values)


def _publication(raw: Mapping[str, Any]) -> Tuple[str, str]:
    reference = _list(_path(raw, "contents", "patentDocument", "bibliographicData", "publicationReference"))
    reference = _mapping(reference[0]) if reference else {}
    ucid = _text(reference.get("ucid"))
    document_ids = _list(reference.get("documentId"))
    document = _mapping(document_ids[0]) if document_ids else {}
    country = _text(_path(document, "country", "content"))
    number = _text(document.get("docNumber"))
    kind = _text(document.get("kind"))
    publication = ucid or "-".join(part for part in (country, number, kind) if part)
    return publication, _text(document.get("date"))


def _party_names(raw: Mapping[str, Any]) -> str:
    parties = _list(_path(raw, "contents", "patentDocument", "bibliographicData", "parties"))
    names: List[str] = []
    for party in parties:
        assignees = _list(_path(party, "assignees", "assignee"))
        for assignee in assignees:
            name = _text(_path(assignee, "addressbook", "name"))
            if name:
                names.append(name)
        # Some documents have no assignee but do have an applicant.
        if not names:
            for applicant in _list(_path(party, "applicants", "applicant")):
                name = _text(_path(applicant, "addressbook", "name")) or _text(
                    _path(applicant, "addressbook", "lastName")
                )
                if name:
                    names.append(name)
    return "; ".join(dict.fromkeys(names))


def _legal_events(raw: Mapping[str, Any]) -> List[Dict[str, str]]:
    status = _list(_path(raw, "contents", "patentDocument", "legalStatus"))
    events: List[Dict[str, str]] = []
    for status_entry in status:
        for event in _list(_mapping(status_entry).get("legal-event")):
            event_data = _mapping(event)
            event_title = _text(_path(event_data, "legal-event-body", "event-title", "$"))
            events.append(
                {
                    "title": event_title,
                    "code": _text(event_data.get("@code")),
                    "date": _text(event_data.get("@date")),
                    "impact": _text(event_data.get("@impact")),
                    "country": _text(event_data.get("@country")),
                }
            )
    return events


def _legal_status_text(events: Sequence[Mapping[str, str]]) -> str:
    return "; ".join(
        " | ".join(part for part in (event.get("title", ""), event.get("code", ""), event.get("date", "")) if part)
        for event in events
    )


def _log_missing(doc_id: str, fields: Iterable[str]) -> None:
    for field in fields:
        logger.warning(
            "SureChEMBL enrichment: doc_id=%s could not extract %s; see FIELD_PATHS and raw_patent.",
            doc_id or "<unknown>",
            field,
        )


def enrich_patent(raw_patent: Any) -> Optional[Dict[str, Any]]:
    """Extract a flat, non-throwing patent record from one raw API object."""
    if not isinstance(raw_patent, dict):
        logger.error("SureChEMBL enrichment skipped non-object patent entry: %r", type(raw_patent).__name__)
        return None

    doc_id = _text(raw_patent.get("doc_id"))
    publication_number, publication_date = _publication(raw_patent)
    patent_document = _mapping(_path(raw_patent, "contents", "patentDocument"))
    bibliographic = _mapping(patent_document.get("bibliographicData"))
    technical = _mapping(bibliographic.get("technicalData"))
    title = _preferred_text(_list(technical.get("inventionTitles")), ("title",))
    assignee = _party_names(raw_patent)
    abstract = _preferred_text(_list(patent_document.get("abstracts")), ("section", "content"))
    claims = _join_sections(patent_document.get("claimResponses"))
    description = _join_sections(patent_document.get("descriptions"))
    family_values = [_text(value) for value in _list(patent_document.get("family"))]
    family_id = next((value for value in family_values if value), "")
    legal_events = _legal_events(raw_patent)
    legal_status = _legal_status_text(legal_events)

    missing = [
        field
        for field, value in (
            ("doc_id", doc_id),
            ("title", title),
            ("publication number", publication_number),
            ("publication date", publication_date),
            ("assignee", assignee),
            ("abstract", abstract),
            ("claims", claims),
            ("description", description),
            ("legal status", legal_status),
            ("patent family", family_id),
        )
        if not value
    ]
    _log_missing(doc_id, missing)
    if not doc_id:
        logger.error("SureChEMBL enrichment skipped record with no doc_id; raw_patent retained only in API debug log.")
        return None

    return {
        "doc_id": doc_id,
        "title": title,
        "publication_number": publication_number,
        "publication_date": publication_date,
        "assignee": assignee,
        "abstract": abstract,
        "claims": claims,
        "description": description,
        "legal_status": legal_status,
        "family_id": family_id,
        "legal_events": legal_events,
        # Deliberately preserve the untouched source object for diagnostics.
        "raw_patent": raw_patent,
    }


def extract_batch_patents(response: Any) -> List[Dict[str, Any]]:
    """Parse every raw patent from the deployed ``/document/batch`` response."""
    if not isinstance(response, dict):
        logger.error("SureChEMBL enrichment received a non-object batch response.")
        return []
    raw_patents = response.get("data")
    if not isinstance(raw_patents, list):
        logger.error(
            "SureChEMBL enrichment expected /document/batch data to be a list, got %s.",
            type(raw_patents).__name__,
        )
        return []
    enriched = [patent for raw in raw_patents if (patent := enrich_patent(raw)) is not None]
    logger.info("SureChEMBL enrichment completed: %d/%d patents contain usable doc_id values.", len(enriched), len(raw_patents))
    return enriched


def print_schema_comparison() -> None:
    print("\n/document/batch parser schema comparison:")
    print("| Field | Expected Path | Actual Path | Status |")
    print("| --- | --- | --- | --- |")
    for field, expected, actual in FIELD_PATHS:
        print(f"| {field} | `{expected}` | `{actual}` | fixed |")


def print_extraction_details(patent: Mapping[str, Any], number: int = 1) -> None:
    """Print requested field-level extraction evidence for one parsed patent."""
    print(f"\nPatent {number} extraction process")
    print("------------------------")
    for field, _, actual_path in FIELD_PATHS:
        key = {
            "publication number": "publication_number",
            "publication date": "publication_date",
            "legal status": "legal_status",
            "patent family": "family_id",
        }.get(field, field)
        value = patent.get(key, "")
        if field == "legal status":
            value = f"{len(_list(patent.get('legal_events')))} event(s)"
        elif field in {"abstract", "claims", "description"}:
            value = f"{len(_text(value))} characters"
        print(f"{field}: {value or 'not available'}")
        print(f"  source: {actual_path}")


def print_verification_summary(patents: Sequence[Mapping[str, Any]]) -> None:
    for index, patent in enumerate(patents, start=1):
        print(f"\nPatent {index}")
        print("------------------------")
        print(f"Doc ID: {patent.get('doc_id') or 'not available'}")
        print(f"Title: {patent.get('title') or 'not available'}")
        print(f"Publication: {patent.get('publication_number') or 'not available'}")
        print(f"Publication Date: {patent.get('publication_date') or 'not available'}")
        print(f"Assignee: {patent.get('assignee') or 'not available'}")
        print(f"Abstract Length: {len(_text(patent.get('abstract')))}")
        print(f"Claims Found: {'yes' if _text(patent.get('claims')) else 'no'}")
        print(f"Description Length: {len(_text(patent.get('description')))}")
        print(f"Legal Events: {len(_list(patent.get('legal_events')))}")
        print(f"Family ID: {patent.get('family_id') or 'not available'}")
