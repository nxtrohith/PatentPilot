"""Output schemas for the patent analysis pipeline.

All LangChain structured-output calls in this project should bind to the
models defined here so that downstream code always receives typed Pydantic
objects rather than raw strings or dicts.

Exported models
---------------
RiskLevel
    Enum of possible freedom-to-operate risk levels.
PatentAnalysisResult
    Primary output model for the patent analysis chain.
Recommendation
    Enum of possible overall recommendations for the report.
PatentReportResult
    Structured output model for the report generation chain.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class RiskLevel(str, Enum):
    """Freedom-to-operate risk classification for the analysed compound.

    Values are ordered from lowest to highest concern:
    LOW → MEDIUM → HIGH → CRITICAL.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Primary output model
# ---------------------------------------------------------------------------


class PatentAnalysisResult(BaseModel):
    """Structured result returned by the patent analysis chain.

    Every field is populated by the LLM via LangChain's structured-output
    mechanism (tool / function calling).  No manual JSON parsing is required.

    Attributes:
        why_retrieved: A concise explanation of why this patent is relevant to
            the query compound — e.g. structural overlap, shared target, or
            identical disease area.
        similarities: Key chemical or pharmacological similarities between the
            query compound and the compounds described in the patent.  Each
            item in the list should describe one distinct similarity.
        potential_overlap: A narrative description of the degree to which the
            query compound might fall within the patent's claimed scope.
            Should reference specific claim language where possible.
        confidence: Model confidence in the analysis as a value in [0.0, 1.0].
            Higher values indicate stronger evidence in the patent text; lower
            values reflect ambiguity or limited information.
        risk_level: Assessed freedom-to-operate risk for a third party wishing
            to develop the query compound.  One of ``"low"``, ``"medium"``,
            ``"high"``, or ``"critical"``.
    """

    why_retrieved: str = Field(
        description=(
            "Concise explanation of why this patent is relevant to the query "
            "compound. Cover structural, mechanistic, or therapeutic area overlap."
        )
    )
    similarities: list[str] = Field(
        description=(
            "List of specific chemical or pharmacological similarities between "
            "the query compound and those described in the patent. "
            "Each element should state one distinct similarity."
        )
    )
    potential_overlap: str = Field(
        description=(
            "Narrative assessment of whether and to what degree the query compound "
            "falls within the patent's claimed scope. Reference claim language "
            "or structural classes where possible."
        )
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Confidence score as a NUMERIC FLOAT in [0.0, 1.0]. "
            "Must be a number such as 0.8, not a word like 'High' or 'Medium'. "
            "1.0 = very high confidence; 0.0 = highly ambiguous or insufficient data."
        ),
    )
    risk_level: RiskLevel = Field(
        description=(
            "Freedom-to-operate risk level: 'low' (minimal overlap), "
            "'medium' (some overlap, design-around possible), "
            "'high' (significant overlap, legal review recommended), "
            "'critical' (compound likely falls squarely within claims)."
        )
    )


# ---------------------------------------------------------------------------
# Report output schema
# ---------------------------------------------------------------------------


class Recommendation(str, Enum):
    """Overall actionable recommendation produced by the report chain.

    Values represent increasing levels of concern:
    PROCEED → PROCEED_WITH_CAUTION → CONSULT_IP_COUNSEL → DO_NOT_PROCEED.
    """

    PROCEED = "proceed"
    PROCEED_WITH_CAUTION = "proceed_with_caution"
    CONSULT_IP_COUNSEL = "consult_ip_counsel"
    DO_NOT_PROCEED = "do_not_proceed"


class PatentReportResult(BaseModel):
    """Structured report produced by the report generation chain.

    Every field is populated by the LLM via LangChain's structured-output
    mechanism (tool / function calling).  No manual JSON parsing is required.

    Attributes:
        executive_summary: A two-to-four sentence overview of the patent
            landscape for the query molecule.  Should state the number of
            patents reviewed, the dominant risk level, and the headline
            finding.
        key_similar_patents: Ordered list of patent titles (most relevant
            first) that share significant chemical or pharmacological
            overlap with the query molecule.  Typically three to five items.
        novelty_concerns: Bullet-point descriptions of the specific aspects
            of the query molecule that may lack novelty or face validity
            challenges based on the reviewed patents.
        patents_requiring_review: Titles of patents that should be reviewed
            by a qualified IP attorney before proceeding.  Drawn from
            patents rated ``high`` or ``critical`` risk.
        overall_recommendation: A single recommended course of action.
            One of ``"proceed"``, ``"proceed_with_caution"``,
            ``"consult_ip_counsel"``, or ``"do_not_proceed"``.
        recommendation_explanation: Two-to-three sentence explanation of
            what drives the overall recommendation.  Should reference
            specific risk levels or concern areas from the analysis.
    """

    executive_summary: str = Field(
        description=(
            "Two-to-four sentence overview of the patent landscape for the query "
            "molecule. State how many patents were reviewed, the dominant risk "
            "level across them, and the headline finding relevant to the molecule."
        )
    )
    key_similar_patents: list[str] = Field(
        description=(
            "Ordered list of patent titles that share the most significant "
            "chemical or pharmacological overlap with the query molecule. "
            "List the most relevant patents first. Typically three to five items; "
            "may be empty if no meaningful overlap was found."
        )
    )
    novelty_concerns: list[str] = Field(
        description=(
            "List of specific aspects of the query molecule that may lack "
            "novelty or face patentability challenges based on the reviewed "
            "patents. Each item describes one distinct concern. May be empty "
            "if no concerns were identified."
        )
    )
    patents_requiring_review: list[str] = Field(
        description=(
            "Titles of patents that warrant review by a qualified IP attorney "
            "before the molecule progresses further. Typically drawn from "
            "patents with 'high' or 'critical' risk levels. May be empty."
        )
    )
    overall_recommendation: Recommendation = Field(
        description=(
            "Overall recommended course of action. "
            "MUST be one of these exact string literals — no other values accepted: "
            "'proceed', 'proceed_with_caution', 'consult_ip_counsel', 'do_not_proceed'. "
            "Meaning: "
            "'proceed' = no significant IP concerns; "
            "'proceed_with_caution' = minor concerns, monitor landscape; "
            "'consult_ip_counsel' = material concerns, legal review needed; "
            "'do_not_proceed' = clear blocking patents identified."
        ),
        examples=["proceed_with_caution"],
    )
    recommendation_explanation: str = Field(
        description=(
            "Two-to-three sentence explanation of what drives the overall "
            "recommendation. Reference specific risk levels, key patents, or "
            "concern areas identified during analysis. Avoid generic language."
        )
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "RiskLevel",
    "PatentAnalysisResult",
    "Recommendation",
    "PatentReportResult",
]
