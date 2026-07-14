"""Exercise the SureChEMBL SMILES-to-patents retrieval workflow.

The response schemas in the published OpenAPI document intentionally leave
``data`` generic.  This script therefore prints every raw JSON response and
only extracts values when a plausible, explicitly named identifier is present.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import replace
from typing import Any, Dict, List, Optional

import requests

from patent_reduction.config import ReductionConfig
from patent_reduction.pipeline.patent_reduction_pipeline import PatentReductionPipeline
from patent_retrieval.batch_fetcher import BatchDocumentFetcher
from patent_retrieval.config import RetrievalConfig
from patent_retrieval.http_session import SureChemblSession
from patent_retrieval.patent_enrichment import (
    print_extraction_details,
    print_schema_comparison,
    print_verification_summary,
)
from patent_retrieval.utils import (
    extract_documents,
    extract_structures,
    first_value_for_keys,
    merge_documents_by_doc_id,
    patent_count,
    response_has_documents,
    values_for_keys,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger("patent_retrieval")


def print_step(step: str, method: str, endpoint: str, params: Optional[dict] = None) -> None:
    print(f"\n=== {step} ===")
    print(f"API endpoint: {method} {endpoint}")
    print(f"Request parameters: {json.dumps(params or {}, sort_keys=True)}")


def request_json(
    session: SureChemblSession,
    step: str,
    method: str,
    endpoint: str,
    *,
    params: Optional[dict] = None,
    payload: Any = None,
    timeout: Optional[tuple] = None,
) -> Any:
    """Make a single SureChEMBL request with retries/timeouts and log the result."""
    print_step(step, method, endpoint, params)
    if payload is not None:
        print(f"Request JSON body: {json.dumps(payload, sort_keys=True)}")

    try:
        response = session.request(
            method, endpoint, params=params, json=payload, timeout=timeout
        )
    except requests.RequestException as exc:
        logger.error("%s %s failed: %s", method, endpoint, exc)
        raise

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


def start_structure_search(
    session: SureChemblSession,
    config: RetrievalConfig,
    smiles: str,
) -> str:
    # The deployed API requires the request fields under this root name.
    # This matches the server's Jackson error response when sent unwrapped.
    payload = {
        "StructureSearchRequest": {
            "struct": smiles,
            "structSearchType": config.search_type,
            "maxResults": config.max_results,
        }
    }
    data = request_json(
        session,
        "1. Start structure search",
        "POST",
        f"{config.base_url}/search/structure",
        payload=payload,
    )
    search_hash = first_value_for_keys(data, {"hash"})
    if not search_hash:
        raise RuntimeError("No search hash found; inspect the raw response above.")
    print(f"Search hash found: {search_hash}")
    return search_hash


def wait_for_completion(
    session: SureChemblSession,
    config: RetrievalConfig,
    search_hash: str,
) -> None:
    endpoint = f"{config.base_url}/search/{search_hash}/status"
    while True:
        data = request_json(
            session,
            "2. Poll search status",
            "GET",
            endpoint,
            timeout=(config.connection_timeout, 30.0),
        )
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
        print(f"Search is still running; waiting {config.poll_seconds:g} seconds...")
        time.sleep(config.poll_seconds)


def retrieve_results(
    session: SureChemblSession,
    config: RetrievalConfig,
    search_hash: str,
) -> Any:
    return request_json(
        session,
        "3. Retrieve structure-search results",
        "GET",
        f"{config.base_url}/search/{search_hash}/results",
        params={"page": 1, "max_results": config.max_results},
    )


def resolve_chemical_id(
    session: SureChemblSession,
    config: RetrievalConfig,
    smiles: str,
) -> str:
    """Resolve the submitted SMILES to SureChEMBL's canonical chemical ID."""
    data = request_json(
        session,
        "1. Resolve SMILES to chemical ID",
        "POST",
        f"{config.base_url}/chemical/smiles/",
        params={"smiles": smiles},
    )
    chemical_id = first_value_for_keys(
        data, {"chemical_id", "chemicalid", "chem_id", "chemid"}
    )
    if not chemical_id:
        raise RuntimeError(
            "SureChEMBL did not return a chemical ID for the submitted SMILES."
        )
    print(f"Chemical ID for submitted SMILES: {chemical_id}")
    return chemical_id


def patent_query_params(
    encoding_name: str,
    chemical_ids: List[str],
    page: int,
    page_size: int,
) -> Any:
    """Build query params for one known SureChEMBL chemicalIds encoding."""
    if encoding_name == "repeated chemicalIds query parameters":
        return [("chemicalIds", chemical_id) for chemical_id in chemical_ids] + [
            ("page", page),
            ("itemsPerPage", page_size),
        ]
    if encoding_name == "comma-separated chemicalIds query parameter":
        return {
            "chemicalIds": ",".join(chemical_ids),
            "page": page,
            "itemsPerPage": page_size,
        }
    return {
        "chemicalIds": json.dumps(chemical_ids),
        "page": page,
        "itemsPerPage": page_size,
    }


def aggregate_patent_response(
    first_response: Any,
    documents: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Return a compact response shape containing all paginated documents."""
    return {
        "data": {
            "results": {
                "total_hits": patent_count(first_response),
                "documents": documents,
            }
        }
    }


def retrieve_patents(
    session: SureChemblSession,
    config: RetrievalConfig,
    chemical_ids: List[str],
) -> Any:
    # The OpenAPI declares chemicalIds as an array query parameter. Its default
    # form serialization is repeated keys, but probe common deployed parsers
    # because the published schema does not specify style/explode explicitly.
    # Once a working encoding is found, page through results up to max_results.
    endpoint = f"{config.base_url}/search/documents_for_structures"
    encodings = [
        "repeated chemicalIds query parameters",
        "comma-separated chemicalIds query parameter",
        "JSON-array chemicalIds query parameter",
    ]

    max_results = max(1, config.max_results)
    page_size = max(1, min(config.page_size, max_results))
    last_response = None

    for encoding_name in encodings:
        print(f"\nTrying chemicalIds encoding: {encoding_name}")
        params = patent_query_params(encoding_name, chemical_ids, page=1, page_size=page_size)
        try:
            response = request_json(
                session,
                f"5. Retrieve patent documents ({encoding_name}, page 1)",
                "POST",
                endpoint,
                params=params,
            )
        except requests.RequestException as exc:
            print(f"Encoding attempt failed: {exc}")
            continue

        last_response = response
        page_documents = extract_documents(response)
        if not page_documents:
            print("This encoding returned no patent documents; trying the next encoding.")
            continue

        print(f"Patent documents found using {encoding_name}.")
        total_hits = patent_count(response)
        all_documents = page_documents[:max_results]
        page = 2

        while len(all_documents) < max_results:
            if total_hits is not None and len(all_documents) >= total_hits:
                break
            params = patent_query_params(
                encoding_name, chemical_ids, page=page, page_size=page_size
            )
            try:
                next_response = request_json(
                    session,
                    f"5. Retrieve patent documents ({encoding_name}, page {page})",
                    "POST",
                    endpoint,
                    params=params,
                )
            except requests.RequestException as exc:
                print(f"Pagination stopped after page {page - 1}: {exc}")
                break

            next_documents = extract_documents(next_response)
            if not next_documents:
                break
            remaining = max_results - len(all_documents)
            all_documents.extend(next_documents[:remaining])
            if len(next_documents) < page_size:
                break
            page += 1

        print(
            f"Retrieved {len(all_documents)} patent document(s) "
            f"out of {total_hits if total_hits is not None else 'unknown'} total hit(s) "
            f"(cap={max_results})."
        )
        return aggregate_patent_response(response, all_documents)

    print(
        "All documented/common chemicalIds encodings returned zero documents. "
        "The raw responses above show whether the IDs were accepted."
    )
    return last_response if last_response is not None else {}


def verify_chemical_ids(
    session: SureChemblSession,
    config: RetrievalConfig,
    chemical_ids: List[str],
) -> Any:
    """Check whether the IDs are recognized by SureChEMBL's chemical API."""
    print(
        "No patent documents were returned. Checking the chemical IDs with "
        "the documented metadata endpoint; this is diagnostic only."
    )
    return request_json(
        session,
        "5b. Verify chemical IDs",
        "POST",
        f"{config.base_url}/chemical/id",
        params={"ids": ",".join(chemical_ids)},
    )


def retrieve_document_details(
    session: SureChemblSession,
    config: RetrievalConfig,
    patent_ids: List[str],
) -> Any:
    # Batch retrieval is the documented endpoint for details for multiple docs.
    # It is now fetched in chunks with automatic retries and failure isolation.
    fetcher = BatchDocumentFetcher(session, config)
    return fetcher.fetch(patent_ids)


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


def print_reduction_result(result: Any) -> None:
    """Print deterministic reduction stats and ranked patent IDs/scores."""
    print("\n=== 7. Patent reduction/ranking ===")
    print("Reduction statistics:")
    print(json.dumps(result.statistics.as_dict(), indent=2, sort_keys=True))

    if not result.reduced_patents:
        print("No patents met the configured reduction filters.")
        return

    print("\nReduced ranked patents:")
    for ranked in result.reduced_patents:
        family_ids = [member.doc_id for member in ranked.family_members]
        print(
            f"#{ranked.rank} {ranked.representative.doc_id} "
            f"final={ranked.scores.final:.2f} scores={ranked.scores.as_dict()} "
            f"familyMembers={family_ids}"
        )


def reduce_patents(
    patent_response: Any,
    detail_response: Any,
    chemical_ids: List[str],
    config: ReductionConfig,
) -> Any:
    """Run the deterministic PatentReductionPipeline over retrieved patents."""
    base_documents = extract_documents(patent_response)
    detail_documents = extract_documents(detail_response)
    raw_patents = merge_documents_by_doc_id(base_documents, detail_documents, chemical_ids)
    pipeline = PatentReductionPipeline(config=config)
    return pipeline.run(raw_patents)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "smiles",
        nargs="?",
        default="CC(=O)Oc1ccccc1C(=O)O",
        help="SMILES to search (default: aspirin)",
    )
    parser.add_argument("--search-type", default=RetrievalConfig.default().search_type)
    parser.add_argument(
        "--max-results",
        type=int,
        default=RetrievalConfig.default().max_results,
        help="Maximum patent documents to retrieve before deterministic reduction.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=RetrievalConfig.default().page_size,
        help="SureChEMBL page size for patent document retrieval.",
    )
    parser.add_argument("--poll-seconds", type=float, default=RetrievalConfig.default().poll_seconds)
    parser.add_argument(
        "--reduction-config",
        help="Optional JSON config file for deterministic patent reduction/ranking.",
    )
    parser.add_argument(
        "--reduction-max-patents",
        type=int,
        default=ReductionConfig().filters.max_patents,
        help="Maximum patents kept after reduction/ranking.",
    )
    parser.add_argument(
        "--reduction-min-score",
        type=float,
        default=ReductionConfig().filters.min_score,
        help="Minimum final score kept after reduction/ranking.",
    )
    parser.add_argument(
        "--batch-chunk-size",
        type=int,
        default=RetrievalConfig.default().batch_chunk_size,
        help="Patent IDs per /document/batch request.",
    )
    parser.add_argument(
        "--retrieval-config",
        help="Optional JSON config file for retrieval settings.",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    reduction_config = ReductionConfig.load(args.reduction_config)
    reduction_config.filters.max_patents = args.reduction_max_patents
    reduction_config.filters.min_score = args.reduction_min_score

    retrieval_config = RetrievalConfig.default()
    if args.retrieval_config:
        import json as _json

        with open(args.retrieval_config, "r", encoding="utf-8") as fh:
            overrides = _json.load(fh)
        retrieval_config = replace(retrieval_config, **overrides)

    retrieval_config = replace(
        retrieval_config,
        search_type=args.search_type,
        max_results=args.max_results,
        page_size=args.page_size,
        poll_seconds=args.poll_seconds,
        batch_chunk_size=args.batch_chunk_size,
    )

    try:
        with SureChemblSession(retrieval_config) as session:
            chemical_id = resolve_chemical_id(session, retrieval_config, args.smiles)
            patent_response = retrieve_patents(
                session,
                retrieval_config,
                [chemical_id],
            )
            total_patents = patent_count(patent_response)
            if total_patents is not None:
                print(f"Total patent documents matching the SMILES: {total_patents:,}")
            if not response_has_documents(patent_response):
                verify_chemical_ids(session, retrieval_config, [chemical_id])
            patent_ids = values_for_keys(
                patent_response,
                {"doc_id", "docid", "document_id", "documentid", "patent_id", "patentid"},
            )
            print(f"Patent IDs found: {patent_ids}")
            details: Any = {}
            if patent_ids:
                details = retrieve_document_details(session, retrieval_config, patent_ids)
                enriched_patents = extract_documents(details)
                if not enriched_patents:
                    raise RuntimeError(
                        "Patent enrichment produced zero usable patents; stopping before "
                        "reduction/ranking. Inspect logs/debug_document_batch_response.json "
                        "and the SureChEMBL enrichment logs."
                    )
                print_schema_comparison()
                print_extraction_details(enriched_patents[0])
                print_verification_summary(enriched_patents)
            else:
                raise RuntimeError(
                    "No patent IDs could be inferred from the search response; stopping "
                    "before enrichment and reduction/ranking."
                )

            reduction_result = reduce_patents(
                patent_response=patent_response,
                detail_response=details,
                chemical_ids=[chemical_id],
                config=reduction_config,
            )
            print_reduction_result(reduction_result)
            return 0
    except (requests.RequestException, RuntimeError, ValueError) as exc:
        print(f"Workflow failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
