"""Tests for the production patent retrieval pipeline services."""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from patent_retrieval.core.config import RetrievalConfig, TOP_PATENTS_LIMIT
from patent_retrieval.services.enrichment_service import (
    _parse_ld_json_abstract,
    _parse_meta_description,
    enrich_missing_abstracts,
)
from patent_retrieval.services.metadata_service import (
    _build_params,
    fetch_patent_details,
    retrieve_patent_ids_for_chemicals,
)
from patent_retrieval.models import ChemicalMatch, PatentResult, RetrievalError
from patent_retrieval.core.pipeline import PatentRetrievalPipeline, _build_patent_results
from patent_retrieval.services.polling_service import poll_until_complete
from patent_retrieval.services.results_service import _parse_chemical_matches, retrieve_search_results
from patent_retrieval.services.search_service import start_similarity_search, validate_smiles


# --------------------------------------------------------------------------- #
# validate_smiles                                                               #
# --------------------------------------------------------------------------- #

class TestValidateSmiles:
    def test_valid_smiles_passes(self) -> None:
        validate_smiles("CC(=O)Oc1ccccc1C(=O)O")  # aspirin — should not raise

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            validate_smiles("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            validate_smiles("   ")

    def test_no_atom_symbols_raises(self) -> None:
        with pytest.raises(ValueError, match="atom"):
            validate_smiles("12345()")


# --------------------------------------------------------------------------- #
# start_similarity_search                                                       #
# --------------------------------------------------------------------------- #

class TestStartSimilaritySearch:
    def _session_returning(self, data: dict) -> MagicMock:
        session = MagicMock()
        session.json_request.return_value = data
        return session

    def test_returns_hash(self) -> None:
        session = self._session_returning({"data": {"hash": "abc123"}})
        config  = RetrievalConfig.default()
        result  = start_similarity_search(session, config, "CC")
        assert result == "abc123"

    def test_raises_on_missing_hash(self) -> None:
        session = self._session_returning({"data": {}})
        with pytest.raises(RetrievalError, match="no search hash"):
            start_similarity_search(session, RetrievalConfig.default(), "CC")

    def test_raises_on_network_error(self) -> None:
        session = MagicMock()
        session.json_request.side_effect = requests.RequestException("boom")
        with pytest.raises(RetrievalError, match="Failed to submit"):
            start_similarity_search(session, RetrievalConfig.default(), "CC")

    def test_payload_contains_smiles(self) -> None:
        session = self._session_returning({"hash": "x"})
        start_similarity_search(session, RetrievalConfig.default(), "CC(=O)O")
        _, kwargs = session.json_request.call_args
        body = kwargs["json"]
        assert body["StructureSearchRequest"]["struct"] == "CC(=O)O"


# --------------------------------------------------------------------------- #
# poll_until_complete                                                           #
# --------------------------------------------------------------------------- #

class TestPollUntilComplete:
    def _cfg(self, **kw) -> RetrievalConfig:
        defaults = dict(
            poll_initial_wait=0.01,
            poll_max_wait=0.05,
            poll_timeout=2.0,
            poll_backoff_factor=2.0,
        )
        defaults.update(kw)
        return RetrievalConfig(**defaults)

    def test_returns_on_finished_status(self) -> None:
        session = MagicMock()
        session.json_request.return_value = {"status": "finished"}
        poll_until_complete(session, self._cfg(), "hash1")
        assert session.json_request.call_count == 1

    def test_returns_on_result_count(self) -> None:
        session = MagicMock()
        session.json_request.return_value = {"resultCount": 42}
        poll_until_complete(session, self._cfg(), "hash1")

    def test_raises_on_failed_status(self) -> None:
        session = MagicMock()
        session.json_request.return_value = {"status": "failed"}
        with pytest.raises(RetrievalError, match="failure"):
            poll_until_complete(session, self._cfg(), "hash1")

    def test_raises_on_timeout(self) -> None:
        session = MagicMock()
        session.json_request.return_value = {"status": "running"}
        with pytest.raises(TimeoutError):
            poll_until_complete(session, self._cfg(poll_timeout=0.05), "hash1")

    def test_exponential_backoff_increases_wait(self) -> None:
        """Each sleep call should be >= the previous one (until cap)."""
        session = MagicMock()
        responses = [
            {"status": "running"},
            {"status": "running"},
            {"status": "finished"},
        ]
        session.json_request.side_effect = responses
        sleep_calls = []
        with patch("patent_retrieval.services.polling_service.time.sleep", side_effect=lambda s: sleep_calls.append(s)):
            poll_until_complete(session, self._cfg(poll_timeout=10.0), "h")
        # First sleep should be shorter or equal to the second.
        assert len(sleep_calls) == 2
        assert sleep_calls[1] >= sleep_calls[0]

    def test_network_error_does_not_immediately_raise(self) -> None:
        session = MagicMock()
        session.json_request.side_effect = [
            requests.RequestException("temporary"),
            {"status": "finished"},
        ]
        with patch("patent_retrieval.services.polling_service.time.sleep"):
            poll_until_complete(session, self._cfg(poll_timeout=5.0), "h")


# --------------------------------------------------------------------------- #
# retrieve_search_results / _parse_chemical_matches                             #
# --------------------------------------------------------------------------- #

class TestRetrieveSearchResults:
    def test_parses_chemical_ids_and_scores(self) -> None:
        structures = [
            {"chemicalId": "SCHEMBL1", "similarity": "0.95"},
            {"chemicalId": "SCHEMBL2", "similarity": "0.80"},
        ]
        matches = _parse_chemical_matches(structures)
        assert len(matches) == 2
        assert matches[0].chemical_id == "SCHEMBL1"
        assert matches[0].similarity_score == pytest.approx(0.95)
        assert matches[1].chemical_id == "SCHEMBL2"

    def test_sorted_descending_by_score(self) -> None:
        structures = [
            {"chemicalId": "A", "score": "0.5"},
            {"chemicalId": "B", "score": "0.9"},
            {"chemicalId": "C", "score": "0.7"},
        ]
        matches = _parse_chemical_matches(structures)
        scores = [m.similarity_score for m in matches]
        assert scores == sorted(scores, reverse=True)

    def test_deduplicates_chemicals(self) -> None:
        structures = [
            {"chemicalId": "X", "similarity": "0.8"},
            {"chemicalId": "X", "similarity": "0.8"},
        ]
        matches = _parse_chemical_matches(structures)
        assert len(matches) == 1

    def test_handles_missing_score_gracefully(self) -> None:
        structures = [{"chemicalId": "Y"}]
        matches = _parse_chemical_matches(structures)
        assert len(matches) == 1
        assert matches[0].similarity_score is None

    def test_raises_retrieval_error_on_network_failure(self) -> None:
        session = MagicMock()
        session.json_request.side_effect = requests.RequestException("down")
        with pytest.raises(RetrievalError):
            retrieve_search_results(session, RetrievalConfig.default(), "h")


# --------------------------------------------------------------------------- #
# _build_params                                                                 #
# --------------------------------------------------------------------------- #

class TestBuildParams:
    def test_repeated_returns_list_of_tuples(self) -> None:
        params = _build_params("repeated", ["A", "B"], page=1, page_size=10)
        assert isinstance(params, list)
        assert ("chemicalIds", "A") in params
        assert ("chemicalIds", "B") in params

    def test_comma_separated_joins_ids(self) -> None:
        params = _build_params("comma-separated", ["A", "B"], page=1, page_size=10)
        assert params["chemicalIds"] == "A,B"

    def test_json_array_encodes_ids(self) -> None:
        import json
        params = _build_params("json-array", ["A", "B"], page=1, page_size=10)
        assert json.loads(params["chemicalIds"]) == ["A", "B"]


# --------------------------------------------------------------------------- #
# _build_patent_results                                                         #
# --------------------------------------------------------------------------- #

class TestBuildPatentResults:
    def _raw_enriched(self, doc_id: str, title: str = "Test") -> dict:
        return {
            "doc_id": doc_id,
            "title": title,
            "publication_number": f"US-{doc_id}-A1",
            "publication_date": "20240101",
            "assignee": "Acme Corp",
            "abstract": "Some abstract.",
            "claims": "",
            "description": "",
            "legal_status": "",
            "family_id": "",
            "legal_events": [],
            "raw_patent": {},
        }

    def test_builds_patent_result_with_score(self) -> None:
        raw = [self._raw_enriched("DOC1")]
        score_map = {"DOC1": 0.91}
        results = _build_patent_results(raw, score_map)
        assert len(results) == 1
        assert results[0].document_id == "DOC1"
        assert results[0].similarity_score == pytest.approx(0.91)
        assert results[0].title == "Test"

    def test_sorted_by_score_descending(self) -> None:
        raw = [self._raw_enriched("A"), self._raw_enriched("B")]
        results = _build_patent_results(raw, {"A": 0.5, "B": 0.9})
        assert results[0].document_id == "B"
        assert results[1].document_id == "A"

    def test_none_score_goes_last(self) -> None:
        raw = [self._raw_enriched("A"), self._raw_enriched("B")]
        results = _build_patent_results(raw, {"A": None, "B": 0.8})
        assert results[0].document_id == "B"
        assert results[-1].document_id == "A"

    def test_skips_non_dict_entries(self) -> None:
        results = _build_patent_results([None, "string", 42], {})  # type: ignore[arg-type]
        assert results == []


# --------------------------------------------------------------------------- #
# enrich_missing_abstracts                                                      #
# --------------------------------------------------------------------------- #

class TestEnrichMissingAbstracts:
    def _config(self) -> RetrievalConfig:
        return RetrievalConfig(google_patents_timeout=5.0)

    def test_passes_through_patents_with_abstracts(self) -> None:
        patent = PatentResult(abstract="Already has one.", document_id="X")
        result = enrich_missing_abstracts([patent], self._config())
        assert result[0].abstract == "Already has one."
        assert result[0].source == "SureChEMBL"

    def test_attempts_enrichment_for_missing_abstract(self) -> None:
        patent = PatentResult(publication_number="US1234567A1")
        with patch(
            "patent_retrieval.services.enrichment_service._fetch_google_abstract",
            return_value="Fetched abstract text.",
        ):
            result = enrich_missing_abstracts([patent], self._config())
        assert result[0].abstract == "Fetched abstract text."
        assert result[0].source == "Google Patents"

    def test_leaves_source_unchanged_on_failed_enrichment(self) -> None:
        patent = PatentResult(publication_number="US9999999A1")
        with patch(
            "patent_retrieval.services.enrichment_service._fetch_google_abstract",
            return_value=None,
        ):
            result = enrich_missing_abstracts([patent], self._config())
        assert result[0].source == "SureChEMBL"
        assert result[0].abstract is None

    def test_skips_if_no_publication_number_or_doc_id(self) -> None:
        patent = PatentResult()  # no identifiers
        with patch(
            "patent_retrieval.services.enrichment_service._fetch_google_abstract"
        ) as mock_fetch:
            enrich_missing_abstracts([patent], self._config())
        mock_fetch.assert_not_called()


# --------------------------------------------------------------------------- #
# HTML parsers                                                                  #
# --------------------------------------------------------------------------- #

class TestHtmlParsers:
    def test_parses_ld_json_abstract(self) -> None:
        html = (
            '<script type="application/ld+json">'
            '{"@type":"Patent","abstract":"The invention relates to..."}'
            "</script>"
        )
        result = _parse_ld_json_abstract(html)
        assert result == "The invention relates to..."

    def test_falls_back_to_description_key(self) -> None:
        html = (
            '<script type="application/ld+json">'
            '{"description":"A compound for treating..."}'
            "</script>"
        )
        assert _parse_ld_json_abstract(html) == "A compound for treating..."

    def test_parses_meta_description(self) -> None:
        html = '<meta name="description" content="Novel synthesis method.">'
        assert _parse_meta_description(html) == "Novel synthesis method."

    def test_returns_none_when_nothing_found(self) -> None:
        assert _parse_ld_json_abstract("<html></html>") is None
        assert _parse_meta_description("<html></html>") is None


# --------------------------------------------------------------------------- #
# PatentRetrievalPipeline (integration, fully mocked)                           #
# --------------------------------------------------------------------------- #

class TestPatentRetrievalPipeline:
    def _make_pipeline(self) -> PatentRetrievalPipeline:
        config = RetrievalConfig(
            poll_initial_wait=0.01,
            poll_max_wait=0.05,
            poll_timeout=2.0,
        )
        return PatentRetrievalPipeline(config=config)

    def test_raises_on_invalid_smiles(self) -> None:
        pipeline = self._make_pipeline()
        with pytest.raises(ValueError):
            pipeline.run("")

    def test_returns_empty_list_when_no_chemical_matches(self) -> None:
        pipeline = self._make_pipeline()
        with (
            patch("patent_retrieval.core.pipeline.start_similarity_search", return_value="h"),
            patch("patent_retrieval.core.pipeline.poll_until_complete"),
            patch("patent_retrieval.core.pipeline.retrieve_search_results", return_value=[]),
        ):
            result = pipeline.run("CC")
        assert result == []

    def test_returns_empty_list_when_no_patent_ids(self) -> None:
        pipeline = self._make_pipeline()
        chemical_matches = [ChemicalMatch("SCHEMBL1", 0.9)]
        with (
            patch("patent_retrieval.core.pipeline.start_similarity_search", return_value="h"),
            patch("patent_retrieval.core.pipeline.poll_until_complete"),
            patch("patent_retrieval.core.pipeline.retrieve_search_results", return_value=chemical_matches),
            patch("patent_retrieval.core.pipeline.retrieve_patent_ids_for_chemicals", return_value=[]),
        ):
            result = pipeline.run("CC")
        assert result == []

    def test_full_pipeline_returns_top_n(self) -> None:
        pipeline = self._make_pipeline()
        chemical_matches = [ChemicalMatch("SCHEMBL1", 0.95)]
        patent_id_scores = [(f"DOC{i}", 0.95) for i in range(15)]
        raw_patents = [
            {
                "doc_id": f"DOC{i}",
                "title": f"Title {i}",
                "publication_number": f"US-DOC{i}-A1",
                "publication_date": "20240101",
                "assignee": "Corp",
                "abstract": f"Abstract {i}",
                "claims": "",
                "description": "",
                "legal_status": "",
                "family_id": "",
                "legal_events": [],
                "raw_patent": {},
            }
            for i in range(15)
        ]
        with (
            patch("patent_retrieval.core.pipeline.start_similarity_search", return_value="h"),
            patch("patent_retrieval.core.pipeline.poll_until_complete"),
            patch("patent_retrieval.core.pipeline.retrieve_search_results", return_value=chemical_matches),
            patch("patent_retrieval.core.pipeline.retrieve_patent_ids_for_chemicals", return_value=patent_id_scores),
            patch("patent_retrieval.core.pipeline.fetch_patent_details", return_value=raw_patents),
            patch("patent_retrieval.core.pipeline.enrich_missing_abstracts", side_effect=lambda patents, cfg: patents),
        ):
            result = pipeline.run("CC", top_n=10)

        assert len(result) == 10
        for p in result:
            assert isinstance(p, PatentResult)

    def test_top_n_respected(self) -> None:
        pipeline = self._make_pipeline()
        chemical_matches = [ChemicalMatch("SCHEMBL1", 0.9)]
        patent_id_scores = [(f"D{i}", 0.9) for i in range(5)]
        raw_patents = [
            {
                "doc_id": f"D{i}",
                "title": "T",
                "publication_number": "US1",
                "publication_date": "20240101",
                "assignee": "X",
                "abstract": "A",
                "claims": "",
                "description": "",
                "legal_status": "",
                "family_id": "",
                "legal_events": [],
                "raw_patent": {},
            }
            for i in range(5)
        ]
        with (
            patch("patent_retrieval.core.pipeline.start_similarity_search", return_value="h"),
            patch("patent_retrieval.core.pipeline.poll_until_complete"),
            patch("patent_retrieval.core.pipeline.retrieve_search_results", return_value=chemical_matches),
            patch("patent_retrieval.core.pipeline.retrieve_patent_ids_for_chemicals", return_value=patent_id_scores),
            patch("patent_retrieval.core.pipeline.fetch_patent_details", return_value=raw_patents),
            patch("patent_retrieval.core.pipeline.enrich_missing_abstracts", side_effect=lambda patents, cfg: patents),
        ):
            result = pipeline.run("CC", top_n=3)

        assert len(result) == 3


# --------------------------------------------------------------------------- #
# PatentResult.to_dict                                                          #
# --------------------------------------------------------------------------- #

class TestPatentResultToDict:
    def test_all_fields_present(self) -> None:
        p = PatentResult(
            publication_number="US-1-A1",
            title="Test",
            publication_date="20240101",
            assignee="Corp",
            abstract="Abstract text.",
            source="SureChEMBL",
            similarity_score=0.91,
            document_id="DOC1",
        )
        d = p.to_dict()
        assert set(d.keys()) == {
            "publication_number", "title", "publication_date",
            "assignee", "abstract", "source", "similarity_score", "document_id",
        }
        assert d["similarity_score"] == pytest.approx(0.91)

    def test_none_values_preserved(self) -> None:
        p = PatentResult()
        d = p.to_dict()
        assert d["publication_number"] is None
        assert d["abstract"] is None
