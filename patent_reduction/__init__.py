"""Deterministic patent reduction & ranking engine (no LLM calls).

Public entry point:

    from patent_reduction.pipeline.patent_reduction_pipeline import PatentReductionPipeline

    result = PatentReductionPipeline().run(raw_patents)
    result.reduced_patents  # ranked, filtered list
    result.statistics       # pipeline funnel stats
"""

from patent_reduction.config import ReductionConfig

__all__ = ["ReductionConfig"]
