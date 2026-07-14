from patent_reduction.config import FilterConfig, ReductionConfig
from patent_reduction.pipeline.patent_reduction_pipeline import PatentReductionPipeline


def make_raw(doc_id, family, similarity, legal_status="Granted", pub_date="2023-01-01"):
    return {
        "doc_id": doc_id,
        "family": family,
        "similarity": similarity,
        "legal_status": legal_status,
        "publication_date": pub_date,
        "matched_chemicals": ["aspirin"],
        "annotations": ["ann1", "ann2"],
        "chemical_ids": ["CHEM1"],
        "title": "Aspirin formulation",
        "abstract": "This invention relates to aspirin.",
        "claims": "1. A composition comprising aspirin.",
        "description": "Detailed description of aspirin usage.",
    }


def test_pipeline_deduplicates_and_collapses_families_and_ranks():
    raw_patents = [
        make_raw("US1", "F1", similarity=0.9),
        make_raw("US1", "F1", similarity=0.9),  # exact duplicate
        make_raw("WO1", "F1", similarity=0.9),  # same family, higher priority country
        make_raw("EP2", "F2", similarity=0.4, legal_status="Rejected"),
    ]

    config = ReductionConfig()
    config.filters = FilterConfig(max_patents=10, min_score=0.0)
    pipeline = PatentReductionPipeline(config=config)

    result = pipeline.run(raw_patents)

    assert result.statistics.initial_patents == 4
    assert result.statistics.after_duplicate_removal == 3
    assert result.statistics.after_family_collapse == 2
    assert result.statistics.final_patents == 2

    top = result.reduced_patents[0]
    assert top.representative.doc_id == "WO1"
    assert {m.doc_id for m in top.family_members} == {"US1"}
    assert top.rank == 1
    assert top.scores.final >= result.reduced_patents[1].scores.final


def test_pipeline_applies_min_score_filter():
    raw_patents = [
        make_raw("US1", "F1", similarity=1.0, legal_status="Granted"),
        make_raw("US2", "F2", similarity=0.0, legal_status="Withdrawn"),
    ]
    config = ReductionConfig()
    config.filters = FilterConfig(max_patents=10, min_score=60.0)
    pipeline = PatentReductionPipeline(config=config)

    result = pipeline.run(raw_patents)
    assert all(rp.scores.final >= 60.0 for rp in result.reduced_patents)


def test_pipeline_applies_max_patents_limit():
    raw_patents = [make_raw(f"US{i}", f"F{i}", similarity=0.9) for i in range(5)]
    config = ReductionConfig()
    config.filters = FilterConfig(max_patents=2, min_score=0.0)
    pipeline = PatentReductionPipeline(config=config)

    result = pipeline.run(raw_patents)
    assert len(result.reduced_patents) == 2
    assert [rp.rank for rp in result.reduced_patents] == [1, 2]


def test_pipeline_handles_missing_similarity_gracefully():
    raw_patents = [
        {"doc_id": "US1", "family": "F1"},
    ]
    config = ReductionConfig()
    config.filters = FilterConfig(max_patents=10, min_score=0.0)
    pipeline = PatentReductionPipeline(config=config)

    result = pipeline.run(raw_patents)
    assert result.statistics.final_patents == 1


def test_pipeline_handles_empty_input():
    config = ReductionConfig()
    pipeline = PatentReductionPipeline(config=config)
    result = pipeline.run([])
    assert result.statistics.initial_patents == 0
    assert result.reduced_patents == []
