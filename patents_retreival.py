"""Exercise the SureChEMBL SMILES-to-patents retrieval workflow.

The response schemas in the published OpenAPI document intentionally leave
``data`` generic.  This script therefore prints every raw JSON response and
only extracts values when a plausible, explicitly named identifier is present.
"""

import argparse
import json
import sys
import time
from typing import Any, Iterable, List, Optional

import requests

BASE_URL = "https://www.surechembl.org/api"
DEFAULT_SEARCH_TYPE = "similarity"
DEFAULT_MAX_RESULTS = 20


def print_step(step: str, method: str, endpoint: str, params: Optional[dict] = None) -> None:
    print(f"\n=== {step} ===")
    print(f"API endpoint: {method} {endpoint}")
    print(f"Request parameters: {json.dumps(params or {}, sort_keys=True)}")


def request_json(
    step: str,
    method: str,
    endpoint: str,
    *,
    params: Optional[dict] = None,
    payload: Any = None,
    timeout: int = 60,
) -> Any:
    print_step(step, method, endpoint, params)
    if payload is not None:
        print(f"Request JSON body: {json.dumps(payload, sort_keys=True)}")

    response = requests.request(
        method,
        endpoint,
        params=params,
        json=payload,
        timeout=timeout,
    )
    print(f"Exact request URL: {response.request.url}")
    print(f"Response status code: {response.status_code}")

    try:
        data = response.json()
    except ValueError:
        print(f"Raw response: {response.text}")
        response.raise_for_status()
        raise RuntimeError("SureChEMBL returned a non-JSON success response")

    print("Raw JSON response:")
    print(json.dumps(data, indent=2, sort_keys=True))
    response.raise_for_status()
    return data


def walk(value: Any) -> Iterable[tuple]:
    """Yield (key, value) pairs recursively without assuming data's shape."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def values_for_keys(data: Any, keys: set) -> List[str]:
    values = []
    for key, value in walk(data):
        if str(key).lower() in keys and isinstance(value, (str, int)):
            text = str(value)
            if text not in values:
                values.append(text)
    return values


def first_value_for_keys(data: Any, keys: set) -> Optional[str]:
    values = values_for_keys(data, keys)
    return values[0] if values else None


def start_structure_search(smiles: str, search_type: str, max_results: int) -> str:
    # The deployed API requires the request fields under this root name.
    # This matches the server's Jackson error response when sent unwrapped.
    payload = {
        "StructureSearchRequest": {
            "struct": smiles,
            "structSearchType": search_type,
            "maxResults": max_results,
        }
    }
    data = request_json(
        "1. Start structure search",
        "POST",
        f"{BASE_URL}/search/structure",
        payload=payload,
    )
    search_hash = first_value_for_keys(data, {"hash"})
    if not search_hash:
        raise RuntimeError("No search hash found; inspect the raw response above.")
    print(f"Search hash found: {search_hash}")
    return search_hash


def wait_for_completion(search_hash: str, poll_seconds: float) -> None:
    endpoint = f"{BASE_URL}/search/{search_hash}/status"
    while True:
        data = request_json("2. Poll search status", "GET", endpoint, timeout=30)
        statuses = [value.lower() for value in values_for_keys(data, {"status", "message"})]
        joined = " ".join(statuses)
        if any(word in joined for word in ("failed", "error")):
            raise RuntimeError(f"Search reported failure: {joined}")
        if any(word in joined for word in ("finished", "complete", "completed", "done")):
            print("Search complete.")
            return
        if values_for_keys(data, {"resultcount"}):
            print("Search complete (resultCount is present).")
            return
        print(f"Search is still running; waiting {poll_seconds:g} seconds...")
        time.sleep(poll_seconds)


def retrieve_results(search_hash: str, max_results: int) -> Any:
    return request_json(
        "3. Retrieve structure-search results",
        "GET",
        f"{BASE_URL}/search/{search_hash}/results",
        params={"page": 1, "max_results": max_results},
    )


def resolve_chemical_id(smiles: str) -> str:
    """Resolve the submitted SMILES to SureChEMBL's canonical chemical ID."""
    data = request_json(
        "1. Resolve SMILES to chemical ID",
        "POST",
        f"{BASE_URL}/chemical/smiles/",
        params={"smiles": smiles},
    )
    chemical_id = first_value_for_keys(
        data, {"chemical_id", "chemicalid", "chem_id", "chemid"}
    )
    if not chemical_id:
        raise RuntimeError("SureChEMBL did not return a chemical ID for the submitted SMILES.")
    print(f"Chemical ID for submitted SMILES: {chemical_id}")
    return chemical_id


def extract_structures(data: Any) -> List[Any]:
    # Structure-search responses contain two structures arrays.  The one under
    # data.query is a list of integer IDs; data.results.structures contains the
    # structure objects and their chemical_id fields.
    if not isinstance(data, dict):
        return []
    response_data = data.get("data")
    if not isinstance(response_data, dict):
        return []
    results = response_data.get("results")
    if not isinstance(results, dict):
        return []
    structures = results.get("structures")
    return structures if isinstance(structures, list) else []


def extract_ids(items: Iterable[Any], keys: set) -> List[str]:
    found = []
    for item in items:
        for value in values_for_keys(item, keys):
            if value not in found:
                found.append(value)
    return found


def response_has_documents(data: Any) -> bool:
    """Return True only when a response contains a non-empty documents list."""
    return any(
        str(key).lower() == "documents"
        and isinstance(value, list)
        and bool(value)
        for key, value in walk(data)
    )


def patent_count(data: Any) -> Optional[int]:
    """Return SureChEMBL's total matching patent-document count, if present."""
    if not isinstance(data, dict):
        return None
    results = data.get("data", {}).get("results", {})
    if not isinstance(results, dict):
        return None
    total_hits = results.get("total_hits")
    if isinstance(total_hits, int):
        return total_hits
    if isinstance(total_hits, str) and total_hits.isdigit():
        return int(total_hits)
    return None


def retrieve_patents(chemical_ids: List[str], page_size: int) -> Any:
    # The OpenAPI declares chemicalIds as an array query parameter. Its default
    # form serialization is repeated keys, but probe common deployed parsers
    # because the published schema does not specify style/explode explicitly.
    endpoint = f"{BASE_URL}/search/documents_for_structures"
    attempts = [
        (
            "repeated chemicalIds query parameters",
            [("chemicalIds", chemical_id) for chemical_id in chemical_ids]
            + [("page", 1), ("itemsPerPage", page_size)],
        ),
        (
            "comma-separated chemicalIds query parameter",
            {
                "chemicalIds": ",".join(chemical_ids),
                "page": 1,
                "itemsPerPage": page_size,
            },
        ),
        (
            "JSON-array chemicalIds query parameter",
            {
                "chemicalIds": json.dumps(chemical_ids),
                "page": 1,
                "itemsPerPage": page_size,
            },
        ),
    ]

    last_response = None
    for encoding_name, params in attempts:
        print(f"\nTrying chemicalIds encoding: {encoding_name}")
        try:
            response = request_json(
                f"5. Retrieve patent documents ({encoding_name})",
                "POST",
                endpoint,
                params=params,
            )
        except requests.RequestException as exc:
            print(f"Encoding attempt failed: {exc}")
            continue

        last_response = response
        if response_has_documents(response):
            print(f"Patent documents found using {encoding_name}.")
            return response
        print("This encoding returned no patent documents; trying the next encoding.")

    print(
        "All documented/common chemicalIds encodings returned zero documents. "
        "The raw responses above show whether the IDs were accepted."
    )
    return last_response if last_response is not None else {}


def verify_chemical_ids(chemical_ids: List[str]) -> Any:
    """Check whether the IDs are recognized by SureChEMBL's chemical API."""
    print(
        "No patent documents were returned. Checking the chemical IDs with "
        "the documented metadata endpoint; this is diagnostic only."
    )
    return request_json(
        "5b. Verify chemical IDs",
        "POST",
        f"{BASE_URL}/chemical/id",
        params={"ids": ",".join(chemical_ids)},
    )


def retrieve_document_details(patent_ids: List[str]) -> Any:
    # Batch retrieval is the documented endpoint for details for multiple docs.
    return request_json(
        "6. Retrieve patent document details",
        "POST",
        f"{BASE_URL}/document/batch",
        params={"doc_ids": ",".join(patent_ids)},
    )


def print_document_fields(data: Any) -> None:
    aliases = {
        "title": {"title", "documenttitle", "patenttitle"},
        "publication number": {
            "publicationnumber",
            "publication_number",
            "publicationno",
            "publication_no",
        },
        "publication date": {"publicationdate", "publication_date", "pubdate"},
        "assignee": {"assignee", "applicant"},
        "abstract": {"abstract"},
    }
    print("\nPatent metadata found in the response:")
    for label, keys in aliases.items():
        matches = [value for value in values_for_keys(data, keys)]
        print(f"{label.title()}: {', '.join(matches) if matches else 'not available'}")
    print("The complete raw JSON response is above; unrecognized fields were not discarded.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("smiles", nargs="?", default="CC(=O)Oc1ccccc1C(=O)O", help="SMILES to search (default: CCO)")
    parser.add_argument("--search-type", default=DEFAULT_SEARCH_TYPE)
    parser.add_argument("--max-results", type=int, default=DEFAULT_MAX_RESULTS)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    args = parser.parse_args()

    try:
        chemical_id = resolve_chemical_id(args.smiles)
        patent_response = retrieve_patents([chemical_id], args.max_results)
        total_patents = patent_count(patent_response)
        if total_patents is not None:
            print(f"Total patent documents matching the SMILES: {total_patents:,}")
        if not response_has_documents(patent_response):
            verify_chemical_ids([chemical_id])
        patent_ids = values_for_keys(
            patent_response,
            {"doc_id", "docid", "document_id", "documentid", "patent_id", "patentid"},
        )
        print(f"Patent IDs found: {patent_ids}")
        if patent_ids:
            details = retrieve_document_details(patent_ids)
            print_document_fields(details)
        else:
            print("No patent IDs could be inferred from the response; raw JSON was printed above.")
        return 0
    except (requests.RequestException, RuntimeError, ValueError) as exc:
        print(f"Workflow failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
