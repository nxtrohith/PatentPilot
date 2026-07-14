from patent_reduction.models import PatentRecord
from patent_reduction.reducers.duplicate_reducer import DuplicateReducer


def make(doc_id: str) -> PatentRecord:
    return PatentRecord.from_raw({"doc_id": doc_id})


def test_removes_exact_duplicates():
    patents = [make("US1"), make("US1"), make("US2")]
    result = DuplicateReducer().reduce(patents)
    assert [p.doc_id for p in result] == ["US1", "US2"]


def test_keeps_all_unique():
    patents = [make("US1"), make("US2"), make("US3")]
    result = DuplicateReducer().reduce(patents)
    assert len(result) == 3


def test_empty_input():
    assert DuplicateReducer().reduce([]) == []
