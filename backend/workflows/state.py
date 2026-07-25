"""Graph state definition for the patent analysis workflow."""

from typing import Annotated, List, Optional, TypedDict
import operator

from patent_retrieval.models import PatentResult
from analysis.schema import PatentAnalysisResult, PatentReportResult


class PatentAnalysisState(TypedDict):
    """Typed state for the LangGraph patent analysis workflow.
    
    Attributes:
        smiles: SMILES string of the compound to analyse.
        disease: Target disease area.
        target: Biological target.
        top_n: Number of patents to retrieve (defaults to 10 if omitted).
        raw_patents: Un-enriched patents from the retrieval pipeline.
        enriched_patents: Patents enriched with missing abstracts.
        patent_analyses: List of (title, analysis_result) pairs from the LLM.
        report: Final synthesized patentability report.
        errors: List of error messages accumulated during graph execution.
    """
    
    # Inputs
    smiles: str
    disease: str
    target: str
    top_n: Optional[int]
    
    # Intermediate Data
    raw_patents: List[PatentResult]
    enriched_patents: List[PatentResult]
    ranked_patents: List[PatentResult]
    patent_analyses: List[tuple[str, PatentAnalysisResult]]
    
    # Final Output
    report: Optional[PatentReportResult]
    
    # Diagnostics / Errors (appends new errors)
    errors: Annotated[List[str], operator.add]
