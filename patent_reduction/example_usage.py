"""Minimal manual sanity-check for the reduction pipeline (not a test).

Run with:  uv run python -m patent_reduction.example_usage
"""

from __future__ import annotations

import json

from patent_reduction.config import ReductionConfig
from patent_reduction.pipeline.patent_reduction_pipeline import PatentReductionPipeline

SAMPLE_PATENTS = [
    {
        "doc_id": "US1000001A1",
        "family": "FAM-1",
        "similarity": 0.97,
        "legal_status": "Granted",
        "publication_date": "2022-05-01",
        "matched_chemicals": ["aspirin"],
        "annotations": ["a1", "a2", "a3"],
        "chemical_ids": ["CHEMBL1"],
        "title": "Aspirin composition",
        "abstract": "Improved aspirin composition for pain relief.",
        "claims": "1. A composition comprising aspirin and a carrier.",
        "description": "Long description mentioning aspirin extensively.",
    },
    {
        "doc_id": "WO1000001A1",
        "family": "FAM-1",  # same family as above -> WO should win as representative
        "similarity": 0.97,
        "legal_status": "Granted",
        "publication_date": "2022-01-01",
        "matched_chemicals": ["aspirin"],
        "annotations": ["a1", "a2", "a3"],
        "chemical_ids": ["CHEMBL1"],
        "title": "Aspirin composition",
        "abstract": "Improved aspirin composition for pain relief.",
        "claims": "1. A composition comprising aspirin and a carrier.",
        "description": "Long description mentioning aspirin extensively.",
    },
    {
        "doc_id": "EP2000002B1",
        "family": "FAM-2",
        "similarity": 0.4,
        "legal_status": "Expired",
        "publication_date": "1998-03-01",
        "matched_chemicals": [],
        "annotations": [],
        "chemical_ids": [],
        "title": "Unrelated chemical process",
        "abstract": "A process for an unrelated chemical.",
        "claims": "1. A process comprising steps X, Y, Z.",
        "description": "No mention of the target molecule.",
    },
]


def main() -> None:
    pipeline = PatentReductionPipeline(config=ReductionConfig())
    result = pipeline.run(SAMPLE_PATENTS)

    print("Statistics:", json.dumps(result.statistics.as_dict(), indent=2))
    for ranked in result.reduced_patents:
        print(
            f"#{ranked.rank} {ranked.representative.doc_id} "
            f"family_members={[m.doc_id for m in ranked.family_members]} "
            f"scores={ranked.scores.as_dict()}"
        )


if __name__ == "__main__":
    main()
