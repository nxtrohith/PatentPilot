"""FastAPI backend for PatentPilot.

Exposes the LangGraph patent analysis workflow as an HTTP API.
Run with: uvicorn api:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import json
import asyncio
from typing import Optional, AsyncGenerator

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv(".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PatentPilot API",
    description="AI-assisted Freedom-to-Operate analysis API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    smiles: str = Field(..., description="SMILES string of the compound to analyze")
    target: Optional[str] = Field(None, description="Biological target (optional)")
    disease: Optional[str] = Field(None, description="Disease / indication (optional)")
    top_n: Optional[int] = Field(8, description="Number of patents to retrieve")


class PatentAnalysisItem(BaseModel):
    title: str
    publication_number: Optional[str]
    assignee: Optional[str]
    publication_date: Optional[str]
    abstract: Optional[str]
    source: Optional[str]
    similarity_score: Optional[float]
    why_retrieved: str
    similarities: list[str]
    potential_overlap: str
    confidence: float
    risk_level: str  # low | medium | high | critical


class AnalyzeResponse(BaseModel):
    smiles: str
    target: Optional[str]
    disease: Optional[str]
    patents: list[PatentAnalysisItem]
    executive_summary: str
    key_similar_patents: list[str]
    novelty_concerns: list[str]
    patents_requiring_review: list[str]
    overall_recommendation: str  # proceed | proceed_with_caution | consult_ip_counsel | do_not_proceed
    recommendation_explanation: str
    errors: list[str]


# ---------------------------------------------------------------------------
# Streaming event helpers
# ---------------------------------------------------------------------------


def _sse(event: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    return {"status": "ok", "service": "PatentPilot API"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    """
    Run the full patent analysis pipeline synchronously.
    Returns the complete structured report once done.
    """
    from workflows import build_patent_workflow

    initial_state = {
        "smiles": req.smiles,
        "disease": req.disease or "",
        "target": req.target or "",
        "top_n": req.top_n or 5,
    }

    logger.info("Starting patent analysis for SMILES: %s", req.smiles)

    try:
        workflow = build_patent_workflow()
        final_state = workflow.invoke(initial_state)
    except Exception as e:
        logger.exception("Workflow failed")
        raise HTTPException(status_code=500, detail=f"Workflow failed: {str(e)}")

    report = final_state.get("report")
    errors = final_state.get("errors", [])
    ranked_patents = final_state.get("ranked_patents", [])
    patent_analyses: list[tuple] = final_state.get("patent_analyses", [])

    # Build a map: patent_title -> analysis result
    analysis_map = {title: result for title, result in patent_analyses}

    # Build patent items
    patent_items: list[PatentAnalysisItem] = []
    for patent in ranked_patents:
        analysis = analysis_map.get(patent.title or "")
        if analysis:
            patent_items.append(
                PatentAnalysisItem(
                    title=patent.title or "Unknown Title",
                    publication_number=patent.publication_number,
                    assignee=patent.assignee,
                    publication_date=patent.publication_date,
                    abstract=patent.abstract,
                    source=patent.source,
                    similarity_score=patent.similarity_score,
                    why_retrieved=analysis.why_retrieved,
                    similarities=analysis.similarities,
                    potential_overlap=analysis.potential_overlap,
                    confidence=analysis.confidence,
                    risk_level=analysis.risk_level.value,
                )
            )

    if report:
        return AnalyzeResponse(
            smiles=req.smiles,
            target=req.target,
            disease=req.disease,
            patents=patent_items,
            executive_summary=report.executive_summary,
            key_similar_patents=report.key_similar_patents,
            novelty_concerns=report.novelty_concerns,
            patents_requiring_review=report.patents_requiring_review,
            overall_recommendation=report.overall_recommendation.value,
            recommendation_explanation=report.recommendation_explanation,
            errors=errors,
        )
    else:
        raise HTTPException(
            status_code=500,
            detail={"message": "Report generation failed", "errors": errors},
        )


@app.post("/analyze/stream")
async def analyze_stream(req: AnalyzeRequest):
    """
    Run the patent analysis pipeline with SSE streaming of progress events.
    
    Events emitted:
      - progress: { step: str, index: int, total: int }
      - result:   full AnalyzeResponse JSON
      - error:    { message: str }
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        steps = [
            "Searching molecular databases",
            "Retrieving relevant patents",
            "Enriching patent metadata",
            "Ranking patents by similarity",
            "Running AI analysis per patent",
            "Generating patentability report",
        ]
        total = len(steps)

        async def emit_progress(index: int):
            yield _sse("progress", {"step": steps[index], "index": index, "total": total})
            await asyncio.sleep(0)

        # We run the heavy workflow in a thread pool to not block the event loop
        import concurrent.futures
        loop = asyncio.get_event_loop()

        # Yield initial progress immediately
        yield _sse("progress", {"step": steps[0], "index": 0, "total": total})
        await asyncio.sleep(0)

        def run_workflow():
            from workflows import build_patent_workflow
            initial_state = {
                "smiles": req.smiles,
                "disease": req.disease or "",
                "target": req.target or "",
                "top_n": req.top_n or 5,
            }
            workflow = build_patent_workflow()
            return workflow.invoke(initial_state)

        try:
            with concurrent.futures.ThreadPoolExecutor() as pool:
                # Simulate step updates while the workflow runs
                future = loop.run_in_executor(pool, run_workflow)

                # Drip progress events while waiting
                step_idx = 1
                while not future.done():
                    await asyncio.sleep(4)
                    if not future.done() and step_idx < total - 1:
                        yield _sse("progress", {"step": steps[step_idx], "index": step_idx, "total": total})
                        step_idx = min(step_idx + 1, total - 2)

                final_state = await future

        except Exception as e:
            logger.exception("Streaming workflow failed")
            yield _sse("error", {"message": str(e)})
            return

        # Final step
        yield _sse("progress", {"step": steps[-1], "index": total - 1, "total": total})
        await asyncio.sleep(0)

        report = final_state.get("report")
        errors = final_state.get("errors", [])
        ranked_patents = final_state.get("ranked_patents", [])
        patent_analyses: list[tuple] = final_state.get("patent_analyses", [])

        analysis_map = {title: result for title, result in patent_analyses}

        patent_items = []
        for patent in ranked_patents:
            analysis = analysis_map.get(patent.title or "")
            if analysis:
                patent_items.append(
                    {
                        "title": patent.title or "Unknown Title",
                        "publication_number": patent.publication_number,
                        "assignee": patent.assignee,
                        "publication_date": patent.publication_date,
                        "abstract": patent.abstract,
                        "source": patent.source,
                        "similarity_score": patent.similarity_score,
                        "why_retrieved": analysis.why_retrieved,
                        "similarities": analysis.similarities,
                        "potential_overlap": analysis.potential_overlap,
                        "confidence": analysis.confidence,
                        "risk_level": analysis.risk_level.value,
                    }
                )

        if report:
            result_payload = {
                "smiles": req.smiles,
                "target": req.target,
                "disease": req.disease,
                "patents": patent_items,
                "executive_summary": report.executive_summary,
                "key_similar_patents": report.key_similar_patents,
                "novelty_concerns": report.novelty_concerns,
                "patents_requiring_review": report.patents_requiring_review,
                "overall_recommendation": report.overall_recommendation.value,
                "recommendation_explanation": report.recommendation_explanation,
                "errors": errors,
            }
            yield _sse("result", result_payload)
        else:
            yield _sse("error", {"message": "Report generation failed", "errors": errors})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
