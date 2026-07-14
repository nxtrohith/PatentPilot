from datetime import date

from patent_reduction.models import PatentRecord
from patent_reduction.scoring.chemical_score import ChemicalEvidenceScorer
from patent_reduction.scoring.claim_score import ClaimImportanceScorer
from patent_reduction.scoring.legal_score import LegalStatusScorer
from patent_reduction.scoring.recency_score import RecencyScorer
from patent_reduction.scoring.structural_score import StructuralScorer


def test_structural_score_normalizes_similarity():
    scorer = StructuralScorer()
    patent = PatentRecord.from_raw({"doc_id": "US1", "similarity": 0.95})
    assert scorer.score(patent) == 95.0


def test_structural_score_uses_neutral_default_when_missing():
    scorer = StructuralScorer()
    patent = PatentRecord.from_raw({"doc_id": "US1"})
    assert scorer.score(patent) == scorer.config.neutral_default_score


def test_chemical_evidence_score_scales_with_counts():
    scorer = ChemicalEvidenceScorer()
    low = PatentRecord.from_raw({"doc_id": "US1", "matched_chemicals": ["a"]})
    high = PatentRecord.from_raw(
        {"doc_id": "US2", "matched_chemicals": ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]}
    )
    assert scorer.score(high) > scorer.score(low)
    assert scorer.score(high) == 100.0


def test_claim_importance_prioritizes_claims_over_description():
    scorer = ClaimImportanceScorer()
    in_claims = PatentRecord.from_raw(
        {"doc_id": "US1", "matched_chemicals": ["aspirin"], "claims": "a compound aspirin is claimed"}
    )
    in_description_only = PatentRecord.from_raw(
        {"doc_id": "US2", "matched_chemicals": ["aspirin"], "description": "aspirin is mentioned here"}
    )
    assert scorer.score(in_claims) > scorer.score(in_description_only)


def test_claim_importance_zero_without_matched_chemicals():
    scorer = ClaimImportanceScorer()
    patent = PatentRecord.from_raw({"doc_id": "US1", "claims": "some unrelated claim text"})
    assert scorer.score(patent) == 0.0


def test_legal_status_granted_positive_expired_negative():
    scorer = LegalStatusScorer()
    granted = PatentRecord.from_raw({"doc_id": "US1", "legal_status": "Granted"})
    expired = PatentRecord.from_raw({"doc_id": "US2", "legal_status": "Expired"})
    assert scorer.score(granted) == 20.0
    assert scorer.score(expired) == -15.0


def test_legal_status_unknown_defaults_to_zero():
    scorer = LegalStatusScorer()
    patent = PatentRecord.from_raw({"doc_id": "US1", "legal_status": "mystery-state"})
    assert scorer.score(patent) == 0.0


def test_recency_score_buckets():
    today = date(2025, 1, 1)
    scorer = RecencyScorer(today=today)
    recent = PatentRecord.from_raw({"doc_id": "US1", "publication_date": "2024-01-01"})
    mid = PatentRecord.from_raw({"doc_id": "US2", "publication_date": "2017-01-01"})
    old = PatentRecord.from_raw({"doc_id": "US3", "publication_date": "1990-01-01"})
    assert scorer.score(recent) == 20.0
    assert scorer.score(mid) == 10.0
    assert scorer.score(old) == 0.0


def test_recency_score_missing_date_defaults_to_zero():
    scorer = RecencyScorer()
    patent = PatentRecord.from_raw({"doc_id": "US1"})
    assert scorer.score(patent) == 0.0
