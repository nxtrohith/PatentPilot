from patent_reduction.models import PatentRecord
from patent_reduction.reducers.family_reducer import FamilyReducer


def make(doc_id: str, family: str, pub_date: str = "2020-01-01") -> PatentRecord:
    return PatentRecord.from_raw(
        {"doc_id": doc_id, "family": family, "publication_date": pub_date}
    )


def test_prefers_wo_over_us():
    patents = [make("US1", "F1"), make("WO1", "F1"), make("EP1", "F1")]
    reps = FamilyReducer().reduce(patents)
    assert len(reps) == 1
    assert reps[0].doc_id == "WO1"
    assert {m.doc_id for m in reps[0].family_members} == {"US1", "EP1"}


def test_tiebreak_by_earliest_publication():
    patents = [
        make("US1", "F1", pub_date="2021-01-01"),
        make("US2", "F1", pub_date="2019-01-01"),
    ]
    reps = FamilyReducer().reduce(patents)
    assert reps[0].doc_id == "US2"


def test_no_family_id_treated_as_own_family():
    patents = [
        PatentRecord.from_raw({"doc_id": "US1"}),
        PatentRecord.from_raw({"doc_id": "US2"}),
    ]
    reps = FamilyReducer().reduce(patents)
    assert len(reps) == 2


def test_unknown_country_falls_back_to_lowest_priority():
    patents = [make("ZZ1", "F1"), make("US1", "F1")]
    reps = FamilyReducer().reduce(patents)
    assert reps[0].doc_id == "US1"
