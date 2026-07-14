"""Top-level patent retrieval pipeline.

Accepts a SMILES string and returns exactly the 10 most relevant patents.

Workflow:
    SMILES
      → validate
      → POST /search/structure           (search_service)
      → GET /search/{hash}/status        (polling_service)
      → GET /search/{hash}/results       (results_service)
      → POST /search/documents_for_structures per chemical  (metadata_service)
      → POST /document/batch             (metadata_service)
      → enrich missing abstracts         (enrichment_service)
      → return top 10 PatentResult objects
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .config import RetrievalConfig, TOP_PATENTS_LIMIT
from .http_session import SureChemblSession
from ..models import PatentResult, RetrievalError
from ..services import (
    enrich_missing_abstracts,
    fetch_patent_details,
    retrieve_patent_ids_for_chemicals,
    enrich_patent,
    poll_until_complete,
    retrieve_search_results,
    start_similarity_search,
    validate_smiles,
)

logger = logging.getLogger(__name__)


class PatentRetrievalPipeline:
    """Orchestrates the full SMILES-to-patents retrieval workflow.

    Usage::

        pipeline = PatentRetrievalPipeline()
        patents  = pipeline.run("CC(=O)Oc1ccccc1C(=O)O")
        for p in patents:
            print(p.to_dict())
    """

    def __init__(self, config: Optional[RetrievalConfig] = None) -> None:
        self.config = config or RetrievalConfig.default()

    def run(
        self,
        smiles: str,
        *,
        top_n: int = TOP_PATENTS_LIMIT,
    ) -> List[PatentResult]:
        """Run the pipeline and return up to ``top_n`` patents.

        Args:
            smiles: SMILES string to search.
            top_n: Maximum number of patents to return (default: 10).

        Returns:
            Up to ``top_n`` :class:`PatentResult` objects sorted by
            similarity score descending.

        Raises:
            ValueError: If SMILES fails basic validation.
            RetrievalError: On unrecoverable API errors.
        """
        validate_smiles(smiles)
        logger.info("PatentRetrievalPipeline.run  smiles=%r  top_n=%d", smiles, top_n)

        with SureChemblSession(self.config) as session:
            return self._execute(session, smiles, top_n)

    # ---------------------------------------------------------------------- #

    def _execute(
        self,
        session: SureChemblSession,
        smiles: str,
        top_n: int,
    ) -> List[PatentResult]:

        # Step 1 – submit similarity search
        search_hash = start_similarity_search(session, self.config, smiles)

        # Step 2 – wait for completion with exponential backoff
        poll_until_complete(session, self.config, search_hash)

        # Step 3 – retrieve chemical matches with similarity scores
        chemical_matches = retrieve_search_results(session, self.config, search_hash)
        if not chemical_matches:
            logger.warning("No chemical matches returned for SMILES: %r", smiles)
            return []

        logger.info(
            "%d chemical match(es). Top score: %s",
            len(chemical_matches),
            f"{chemical_matches[0].similarity_score:.3f}"
            if chemical_matches[0].similarity_score is not None else "N/A",
        )

        # Step 4 – resolve chemicals → patent IDs, preserving similarity scores
        # Fetch up to top_n*3 so we have headroom after metadata failures.
        patent_id_scores = retrieve_patent_ids_for_chemicals(
            session, self.config, chemical_matches, limit=top_n * 3
        )
        if not patent_id_scores:
            logger.warning("No patent IDs could be resolved from chemical matches.")
            return []

        # Cap before heavy batch fetch to avoid unnecessary work.
        patent_id_scores = patent_id_scores[: top_n * 2]
        patent_ids  = [pid for pid, _ in patent_id_scores]
        score_by_id = {pid: score for pid, score in patent_id_scores}

        # Step 5 – batch-fetch full patent metadata
        raw_patents = fetch_patent_details(session, self.config, patent_ids)
        if not raw_patents:
            logger.warning("Patent metadata fetch returned no usable records.")
            return []

        # Step 6 – build PatentResult objects
        results = _build_patent_results(raw_patents, score_by_id)
        logger.info(
            "Built %d PatentResult(s) from %d raw record(s).",
            len(results), len(raw_patents),
        )

        # Step 7 – enrich missing abstracts from Google Patents
        results = enrich_missing_abstracts(results, self.config)

        # Step 8 – return top N
        top = results[:top_n]
        logger.info("Pipeline complete. Returning %d patent(s).", len(top))
        return top


def _build_patent_results(
    raw_patents: List[Any],
    score_by_id: Dict[str, Optional[float]],
) -> List[PatentResult]:
    """Convert raw patent dicts into PatentResult objects with scores attached.

    Accepts both pre-enriched records (output of extract_batch_patents) and
    plain dicts from the generic extract_documents fallback path.
    """
    results: List[PatentResult] = []

    for raw in raw_patents:
        if not isinstance(raw, dict):
            continue

        # Already enriched by extract_batch_patents / enrich_patent.
        if "publication_number" in raw and "doc_id" in raw:
            enriched: Optional[Dict[str, Any]] = raw
        else:
            enriched = enrich_patent(raw)

        if enriched is None:
            continue

        doc_id = enriched.get("doc_id") or ""

        results.append(
            PatentResult(
                publication_number=enriched.get("publication_number") or None,
                title=enriched.get("title") or None,
                publication_date=enriched.get("publication_date") or None,
                assignee=enriched.get("assignee") or None,
                abstract=enriched.get("abstract") or None,
                source="SureChEMBL",
                similarity_score=score_by_id.get(doc_id),
                document_id=doc_id or None,
            )
        )

    # Sort: scored entries descend by score; unscored at the end.
    return sorted(
        results,
        key=lambda p: (p.similarity_score is None, -(p.similarity_score or 0.0)),
    )
