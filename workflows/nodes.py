"""LangGraph node implementations."""

import logging
from typing import Dict, Any

from .state import PatentAnalysisState
from patent_retrieval.core.pipeline import PatentRetrievalPipeline
from patent_retrieval.services import enrich_missing_abstracts
from patent_retrieval.core.config import RetrievalConfig
from llm.provider import get_llm
from chains.patent_analysis import PatentAnalysisInput
from analysis.service import PatentAnalysisService
from chains.report_generation import ReportGenerationInput
from analysis.report_service import ReportGenerationService

logger = logging.getLogger(__name__)


def retrieve_patents_node(state: PatentAnalysisState) -> Dict[str, Any]:
    """Retrieve raw patents based on SMILES string."""
    smiles = state.get("smiles")
    if not smiles:
        return {"errors": ["No SMILES string provided."]}
        
    logger.info("Executing retrieve_patents_node for SMILES: %s", smiles)
    try:
        top_n = state.get("top_n") or 10
        
        # Check cache first
        from patent_retrieval.database import load_patents, save_patents
        cached_patents = load_patents(query_smiles=smiles, limit=top_n)
        if cached_patents:
            logger.info("Found %d cached patents for SMILES: %s", len(cached_patents), smiles)
            return {"raw_patents": cached_patents}
        
        pipeline = PatentRetrievalPipeline()
        raw_patents = pipeline.run(smiles, top_n=top_n)
        
        # Save to cache
        if raw_patents:
            save_patents(raw_patents, query_smiles=smiles)
            
        return {"raw_patents": raw_patents}
    except Exception as e:
        logger.exception("Error in retrieve_patents_node")
        return {"errors": [f"Retrieval failed: {str(e)}"]}


def enrich_patents_node(state: PatentAnalysisState) -> Dict[str, Any]:
    """Enrich missing abstracts for the retrieved patents."""
    raw_patents = state.get("raw_patents", [])
    if not raw_patents:
        logger.warning("No raw patents to enrich.")
        return {"enriched_patents": []}
        
    logger.info("Executing enrich_patents_node for %d patents", len(raw_patents))
    try:
        config = RetrievalConfig.default()
        enriched = enrich_missing_abstracts(raw_patents, config)
        return {"enriched_patents": enriched}
    except Exception as e:
        logger.exception("Error in enrich_patents_node")
        return {"errors": [f"Enrichment failed: {str(e)}"], "enriched_patents": raw_patents}


def rank_patents_node(state: PatentAnalysisState) -> Dict[str, Any]:
    """Rank enriched patents using Python heuristic and keep the top 5.
    
    EXTENSION POINT: Reranking
    --------------------------
    This is the ideal place to introduce a Cross-Encoder or an LLM-as-a-judge
    to re-rank the retrieved patents based on semantic similarity to the query
    molecule, rather than relying solely on the SureChEMBL structural similarity
    score.
    """
    enriched = state.get("enriched_patents", [])
    if not enriched:
        logger.warning("No enriched patents to rank.")
        return {"ranked_patents": []}
        
    logger.info("Executing rank_patents_node for %d patents", len(enriched))
    try:
        def score_patent(p):
            score = p.similarity_score if p.similarity_score is not None else 0.0
            # Tie breaker: favor patents with an abstract or title
            if p.abstract:
                score += 0.001
            if p.title:
                score += 0.001
            return score
            
        ranked = sorted(enriched, key=score_patent, reverse=True)
        top_5 = ranked[:5]
        return {"ranked_patents": top_5}
    except Exception as e:
        logger.exception("Error in rank_patents_node")
        return {"errors": [f"Ranking failed: {str(e)}"], "ranked_patents": enriched[:5]}


def analyze_patents_node(state: PatentAnalysisState) -> Dict[str, Any]:
    """Run structured patent analysis on ranked patents."""
    ranked = state.get("ranked_patents", [])
    if not ranked:
        logger.warning("No ranked patents to analyze.")
        return {"patent_analyses": []}
        
    logger.info("Executing analyze_patents_node for %d patents", len(ranked))
    try:
        inputs = []
        for p in ranked:
            inputs.append(PatentAnalysisInput(
                smiles=state["smiles"],
                patent_title=p.title or "Unknown Title",
                patent_abstract=p.abstract or "",
                publication_date=p.publication_date or "",
                assignee=p.assignee or "",
                disease=state.get("disease", ""),
                target=state.get("target", "")
            ))
            
        llm = get_llm()
        service = PatentAnalysisService(llm)
        batch_results = service.analyse_batch(inputs)
        
        analyses = []
        errors = []
        for res in batch_results:
            if res.success and res.result:
                analyses.append((res.patent_title, res.result))
            else:
                errors.append(f"Analysis failed for '{res.patent_title}': {res.error}")
                
        return {"patent_analyses": analyses, "errors": errors}
    except Exception as e:
        logger.exception("Error in analyze_patents_node")
        return {"errors": [f"Analysis node failed: {str(e)}"]}


def aggregate_results_node(state: PatentAnalysisState) -> Dict[str, Any]:
    """Aggregate analysis results.
    
    EXTENSION POINT: Claim Analysis
    -------------------------------
    This node currently acts as a passthrough or logging step, but prepares the 
    architecture for future aggregation logic. Specifically, this is where a
    dedicated `ClaimAnalysisService` could be invoked to parse and analyze the
    independent and dependent claims of the highest-ranked patents.
    """
    analyses = state.get("patent_analyses", [])
    logger.info("Executing aggregate_results_node. Aggregated %d successful analyses.", len(analyses))
    return {}


def generate_report_node(state: PatentAnalysisState) -> Dict[str, Any]:
    """Generate the final patent landscape report based on the analyses."""
    analyses = state.get("patent_analyses", [])
    if not analyses:
        logger.warning("No analyses available for report generation.")
        return {"errors": ["No analyses available for report generation."]}
        
    logger.info("Executing generate_report_node with %d analyses", len(analyses))
    try:
        input_data = ReportGenerationInput(
            smiles=state["smiles"],
            disease=state.get("disease", ""),
            target=state.get("target", ""),
            analyses=analyses
        )
        
        llm = get_llm()
        service = ReportGenerationService(llm)
        report = service.generate(input_data)
        
        return {"report": report}
    except Exception as e:
        logger.exception("Error in generate_report_node")
        return {"errors": [f"Report generation failed: {str(e)}"]}
