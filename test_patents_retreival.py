import unittest

from patents_retreival import patent_count, values_for_keys


class PatentCountTests(unittest.TestCase):
    def test_extracts_numeric_total_hits(self) -> None:
        response = {"data": {"results": {"total_hits": 693404, "documents": []}}}

        self.assertEqual(patent_count(response), 693404)

    def test_extracts_string_total_hits(self) -> None:
        self.assertEqual(patent_count({"data": {"results": {"total_hits": "42"}}}), 42)

    def test_returns_none_when_total_hits_is_missing_or_invalid(self) -> None:
        self.assertIsNone(patent_count({"data": {"results": {}}}))
        self.assertIsNone(patent_count({"data": {"results": {"total_hits": "unknown"}}}))

    def test_extracts_surechembl_camel_case_document_ids(self) -> None:
        response = {"data": {"results": {"documents": [{"docId": "CN-104387360-B"}]}}}

        self.assertEqual(
            values_for_keys(response, {"doc_id", "docid", "document_id", "documentid"}),
            ["CN-104387360-B"],
        )


if __name__ == "__main__":
    unittest.main()
