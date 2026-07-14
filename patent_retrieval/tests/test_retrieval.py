"""Unit tests for the production-ready patent retrieval pipeline."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from patent_retrieval.batch_fetcher import BatchDocumentFetcher
from patent_retrieval.config import RetrievalConfig
from patent_retrieval.http_session import SureChemblSession, build_retry_strategy
from patent_retrieval.progress_tracker import RetrievalProgressTracker
from patent_retrieval.utils import (
    extract_documents,
    merge_documents_by_doc_id,
    patent_count,
    values_for_keys,
)


class TestRetrievalConfig:
    def test_default_config_values(self) -> None:
        config = RetrievalConfig.default()
        assert config.base_url == "https://www.surechembl.org/api"
        assert config.batch_chunk_size == 40
        assert config.max_retries == 3
        assert config.chunk_retries == 1
        assert config.timeout == (10.0, 60.0)

    def test_invalid_batch_chunk_size(self) -> None:
        with pytest.raises(ValueError, match="batch_chunk_size"):
            RetrievalConfig(batch_chunk_size=0)

    def test_invalid_max_results(self) -> None:
        with pytest.raises(ValueError, match="max_results"):
            RetrievalConfig(max_results=0)


class TestBuildRetryStrategy:
    def test_retry_status_codes(self) -> None:
        config = RetrievalConfig.default()
        retry = build_retry_strategy(config)
        assert retry.total == config.max_retries
        assert config.retry_status_codes.issubset(retry.status_forcelist)


class TestSureChemblSession:
    def test_request_passes_timeout(self) -> None:
        session = SureChemblSession(RetrievalConfig.default())
        with patch.object(session._session, "request", return_value=MagicMock()) as mock_request:
            session.request("GET", "https://example.com/test")
            _, _, kwargs = mock_request.mock_calls[0]
            assert kwargs["timeout"] == (10.0, 60.0)

    def test_context_manager_closes_session(self) -> None:
        with patch("patent_retrieval.http_session.create_session") as mock_create:
            mock_session = MagicMock()
            mock_create.return_value = mock_session
            with SureChemblSession(RetrievalConfig.default()) as session:
                pass
            mock_session.close.assert_called_once()


class TestBatchDocumentFetcher:
    def _make_session(self, responses: list) -> SureChemblSession:
        """Return a session whose requests cycle through the provided responses."""
        session = SureChemblSession(RetrievalConfig.default())
        mock_response = MagicMock()
        mock_response.json.side_effect = responses
        mock_response.raise_for_status.side_effect = [None] * len(responses)
        mock_response.request.url = "https://example.com/document/batch"
        session._session.request = MagicMock(return_value=mock_response)
        return session

    def test_chunking_and_merge(self) -> None:
        config = RetrievalConfig(batch_chunk_size=2, chunk_retries=0)
        session = self._make_session([
            {"data": {"results": {"documents": [{"docId": "A1"}, {"docId": "B1"}]}}},
            {"data": {"results": {"documents": [{"docId": "C1"}]}}},
        ])
        fetcher = BatchDocumentFetcher(session, config)
        result = fetcher.fetch(["A1", "B1", "C1"])

        documents = extract_documents(result)
        assert len(documents) == 3
        assert session._session.request.call_count == 2

    def test_failed_chunk_continues(self) -> None:
        config = RetrievalConfig(batch_chunk_size=1, chunk_retries=0)
        session = self._make_session([
            {"data": {"results": {"documents": [{"docId": "A1"}]}}},
        ])
        # Second chunk fails via RequestException.
        session._session.request.side_effect = [
            MagicMock(
                json=MagicMock(return_value={"data": {"results": {"documents": [{"docId": "A1"}]}}}),
                raise_for_status=MagicMock(),
                request=MagicMock(url="https://example.com/document/batch"),
            ),
            requests.RequestException("boom"),
        ]
        fetcher = BatchDocumentFetcher(session, config)
        result = fetcher.fetch(["A1", "B2"])

        documents = extract_documents(result)
        assert len(documents) == 1
        summary = result["data"]["results"]["retrieval_summary"]
        assert summary["failed_ids"] == 1
        assert summary["chunks_failed"] == 1


class TestUtils:
    def test_values_for_keys(self) -> None:
        data = {"a": {"B": 1}, "c": [{"d": 2}]}
        assert values_for_keys(data, {"b", "d"}) == ["1", "2"]

    def test_patent_count(self) -> None:
        assert patent_count({"data": {"results": {"total_hits": 42}}}) == 42
        assert patent_count({"data": {"results": {"total_hits": "42"}}}) == 42
        assert patent_count({"data": {"results": {}}}) is None

    def test_extract_documents(self) -> None:
        data = {"data": {"results": {"documents": [{"docId": "A"}, {"docId": "B"}]}}}
        docs = extract_documents(data)
        assert len(docs) == 2

    def test_merge_documents_by_doc_id(self) -> None:
        base = [{"docId": "A", "title": "base"}]
        detail = [{"doc_id": "A", "abstract": "detail"}]
        merged = merge_documents_by_doc_id(base, detail, ["CHEM1"])
        assert len(merged) == 1
        assert merged[0]["abstract"] == "detail"
        assert merged[0]["chemical_ids"] == ["CHEM1"]
