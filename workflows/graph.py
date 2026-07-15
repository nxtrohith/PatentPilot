"""LangGraph patent analysis workflow compilation."""

from langgraph.graph import StateGraph, START, END
from .state import PatentAnalysisState
from .nodes import (
    retrieve_patents_node,
    enrich_patents_node,
    rank_patents_node,
    analyze_patents_node,
    aggregate_results_node,
    generate_report_node,
)


def build_patent_workflow():
    """Build and compile the patent analysis workflow.
    
    Returns:
        Compiled LangGraph application ready for `invoke`.
    """
    workflow = StateGraph(PatentAnalysisState)
    
    # Add nodes
    workflow.add_node("retrieve", retrieve_patents_node)
    workflow.add_node("enrich", enrich_patents_node)
    workflow.add_node("rank", rank_patents_node)
    workflow.add_node("analyze", analyze_patents_node)
    workflow.add_node("aggregate", aggregate_results_node)
    workflow.add_node("report", generate_report_node)
    
    # Add edges
    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "enrich")
    workflow.add_edge("enrich", "rank")
    workflow.add_edge("rank", "analyze")
    workflow.add_edge("analyze", "aggregate")
    workflow.add_edge("aggregate", "report")
    workflow.add_edge("report", END)
    
    return workflow.compile()

# Instantiate the compiled graph so LangGraph CLI can import it
graph = build_patent_workflow()
