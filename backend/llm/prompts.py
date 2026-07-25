"""Prompt templates for PatentPilot's LLM interactions.

This module provides a centralized, modular collection of LangChain
ChatPromptTemplate instances used throughout the application.  Each prompt
is defined as a named constant so that call-sites can import only what they
need.  Adding a new prompt is as simple as appending a new template below
and exporting it from __all__.

Available prompts
-----------------
PATENT_ANALYSIS_PROMPT
    Instructs the model to answer four specific dashboard questions about a
    retrieved patent, using only the supplied metadata — no fabrication.
REPORT_GENERATION_PROMPT
    Synthesises a list of per-patent analyses into a structured research
    report covering executive summary, novelty concerns, and a concrete
    overall recommendation.
"""

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

# ---------------------------------------------------------------------------
# System persona
# ---------------------------------------------------------------------------

_PATENT_ANALYST_SYSTEM = SystemMessagePromptTemplate.from_template(
    """You are a pharmaceutical patent analyst supporting a patent review dashboard.

Your task is to answer exactly four questions about a retrieved patent, using
ONLY the metadata supplied in the user message.  Strict rules apply:

- Base every answer on the supplied metadata alone.  Do NOT fabricate, infer,
  or assume information that is not present in the provided fields.
- Clearly label facts (drawn directly from the metadata) versus assumptions
  (reasonable inferences you flag explicitly).
- If patent claims are not provided, state that limitation explicitly instead
  of guessing at claim scope.
- Keep each answer concise and suitable for a dashboard card — one to three
  sentences per section unless the evidence demands more detail.
- Use plain, precise language accessible to both scientists and IP reviewers."""
)

# ---------------------------------------------------------------------------
# Patent analysis prompt — four structured dashboard questions
# ---------------------------------------------------------------------------

_PATENT_ANALYSIS_HUMAN = HumanMessagePromptTemplate.from_template(
    """You have been given the following compound and patent metadata.

## Compound Under Review
- **SMILES**: {smiles}

## Retrieved Patent Metadata
- **Title**: {patent_title}
- **Abstract**: {patent_abstract}
- **Publication Date**: {publication_date}
- **Assignee**: {assignee}{optional_context}

---

Answer the four questions below.  Structure your response with the exact
section headers shown.  Base every statement solely on the metadata above.

### 1. Why Was This Patent Retrieved?
Explain what triggered retrieval of this patent relative to the compound
under review.  Identify the primary matching signal — e.g. shared chemical
scaffold, same therapeutic target, overlapping disease area, or common
assignee/inventor.  If the abstract is absent or uninformative, say so.

### 2. Which Aspects Appear Similar?
List the specific chemical, pharmacological, or therapeutic aspects that the
patent and the query compound share.  For each point, state whether it is a
**Fact** (explicitly present in the metadata) or an **Assumption** (a
reasonable chemical inference you are flagging).

### 3. What Possible Overlap Exists?
Assess the degree to which the query compound may fall within the scope of
this patent.  Reference the title, abstract language, or disease/target fields
where available.  If no claims text has been provided, explicitly state:
"Patent claims were not supplied; overlap assessment is limited to the abstract
and title."

### 4. What Is the Confidence Level?
State your overall confidence in this analysis as one of:
**High** | **Medium** | **Low** | **Insufficient data**

Then explain in one or two sentences what drives that rating — e.g. richness
of the abstract, presence or absence of claims, relevance of the disease/target
fields, or structural clarity of the SMILES."""
)

# Optional context block — appended to the human message when disease/target are provided
_OPTIONAL_CONTEXT_TEMPLATE = """
- **Disease Area**: {disease}
- **Biological Target**: {target}"""


def _build_optional_context(disease: str | None, target: str | None) -> str:
    """Return a formatted optional-context block or an empty string."""
    parts: list[str] = []
    if disease:
        parts.append(f"- **Disease Area**: {disease}")
    if target:
        parts.append(f"- **Biological Target**: {target}")
    if not parts:
        return ""
    return "\n" + "\n".join(parts)


# The base template (system + human).  Call-sites should use
# `build_patent_analysis_messages()` to get a fully populated list of messages.
PATENT_ANALYSIS_PROMPT: ChatPromptTemplate = ChatPromptTemplate.from_messages(
    [_PATENT_ANALYST_SYSTEM, _PATENT_ANALYSIS_HUMAN]
)
"""ChatPromptTemplate for the patent review dashboard.

Required input variables
------------------------
smiles : str
    SMILES representation of the compound under review.
patent_title : str
    Title of the retrieved patent.
patent_abstract : str
    Abstract / summary of the patent.  Pass an empty string and the model
    will flag the limitation; never pass fabricated text.
publication_date : str
    Publication or priority date (e.g. ``"2023-06-15"``).
assignee : str
    Patent assignee / applicant name.
optional_context : str
    Pre-formatted optional context string produced by
    ``_build_optional_context()``.  Pass an empty string when neither
    disease nor target is available.
"""


# ---------------------------------------------------------------------------
# Public helper — preferred entry point for callers
# ---------------------------------------------------------------------------


def build_patent_analysis_messages(
    smiles: str,
    patent_title: str,
    patent_abstract: str,
    publication_date: str,
    assignee: str,
    disease: str | None = None,
    target: str | None = None,
) -> list:
    """Format and return the patent-analysis prompt as a list of messages.

    This is the recommended way to obtain prompt messages for the patent
    analysis workflow.  It handles the optional *disease* and *target*
    fields gracefully so callers do not need to manage the
    ``optional_context`` placeholder directly.

    Args:
        smiles: SMILES string of the compound to analyse.
        patent_title: Title of the retrieved patent.
        patent_abstract: Abstract text of the patent.  Pass an empty string
            when unavailable; do NOT fabricate text.
        publication_date: Publication or filing date (free-form string).
        assignee: Patent assignee / applicant name.
        disease: Optional therapeutic disease area (e.g. ``"Type 2 Diabetes"``).
        target: Optional biological target (e.g. ``"GLP-1 Receptor"``).

    Returns:
        A list of ``BaseMessage`` objects ready to be passed directly to
        any LangChain chat model (``llm.invoke(messages)``).

    Example::

        from llm.prompts import build_patent_analysis_messages
        from llm.provider import get_llm

        messages = build_patent_analysis_messages(
            smiles="CC(=O)Oc1ccccc1C(=O)O",
            patent_title="Novel salicylate derivatives ...",
            patent_abstract="The present invention relates to ...",
            publication_date="2022-03-10",
            assignee="Pharma Corp Ltd",
            disease="Pain",
            target="COX-2",
        )
        response = get_llm().invoke(messages)
        print(response.content)
    """
    optional_context = _build_optional_context(disease, target)
    return PATENT_ANALYSIS_PROMPT.format_messages(
        smiles=smiles,
        patent_title=patent_title,
        patent_abstract=patent_abstract,
        publication_date=publication_date,
        assignee=assignee,
        optional_context=optional_context,
    )


# ---------------------------------------------------------------------------
# Report generation prompt
# ---------------------------------------------------------------------------

_REPORT_ANALYST_SYSTEM = SystemMessagePromptTemplate.from_template(
    """You are a senior pharmaceutical patent analyst preparing a formal IP
landscape report for a drug discovery research team.

Your task is to synthesise a set of individual per-patent analyses into a
concise, actionable report.  The audience is researchers who need clear
guidance — not legal counsel — so balance precision with readability.

Strict rules:
- Base every conclusion solely on the provided patent analyses.  Do NOT
  introduce external knowledge or invent patents not listed.
- Clearly distinguish patterns observed across multiple patents from
  observations about individual patents.
- Use definitive, professional language.  Avoid hedging phrases such as
  "it may be possible" when the data allows a clear conclusion.
- If the analysis list is empty or all patents have low confidence, say so
  explicitly in the executive summary instead of fabricating findings.
- Keep each section tight: researchers scan reports; do not pad."""
)

_REPORT_GENERATION_HUMAN = HumanMessagePromptTemplate.from_template(
    """Prepare a patent landscape report for the following molecule and indication.

## Molecule Under Review
- **SMILES**: {smiles}
- **Disease Area**: {disease}
- **Biological Target**: {target}

## Patent Analyses ({patent_count} patents reviewed)

{analyses_block}

---

Using ONLY the patent analyses above, produce a structured report with these
exact sections:

### Executive Summary
Two to four sentences covering: total patents reviewed, dominant risk level,
and the headline IP finding for this molecule.

### Key Similar Patents
An ordered list of the patent titles most relevant to this molecule (most
concerning first).  Include only patents with meaningful overlap.  Omit
patents with no relevant similarity.

### Potential Novelty Concerns
Bullet-point list of specific aspects of the molecule that may face novelty
or patentability challenges based on the reviewed patents.  Be specific:
name the structural feature, biological target, or therapeutic use at issue.
If no concerns exist, write: "No significant novelty concerns identified."

### Patents Requiring Manual Review
List the titles of any patents rated high or critical risk, or any patent
where confidence is ≥ 0.7 and overlap is non-trivial.  These require review
by a qualified IP attorney before the molecule advances.  If none qualify,
write: "No patents require immediate manual review."

### Overall Recommendation
One of: Proceed | Proceed with Caution | Consult IP Counsel | Do Not Proceed

### Explanation of Recommendation
Two to three sentences explaining the recommendation.  Reference the specific
risk drivers — name patents, risk levels, or concern areas.  Do not repeat
the executive summary."""
)


def _format_analyses_block(
    analyses: list[tuple[str, object]],
) -> tuple[str, int]:
    """Render a list of (patent_title, PatentAnalysisResult) pairs as a text block.

    Returns a (block_text, count) tuple.  The block is injected verbatim into
    the report prompt template; the count drives the ``{patent_count}`` slot.

    Each analysis is rendered as a numbered section with labelled fields so
    the model receives structured, scannable context rather than raw JSON.

    Args:
        analyses: List of ``(patent_title, PatentAnalysisResult)`` tuples.
            ``PatentAnalysisResult`` is not imported at module level to avoid
            the circular import; it is accessed via attribute access only.

    Returns:
        Tuple of (formatted block string, number of analyses).
    """
    if not analyses:
        return "No patent analyses available.", 0

    lines: list[str] = []
    for i, (title, result) in enumerate(analyses, start=1):
        similarities = "\n".join(
            f"    - {s}" for s in (result.similarities or ["None noted"])
        )
        lines.append(
            f"""[Patent {i}]
Title            : {title}
Risk Level       : {result.risk_level.value.upper()}
Confidence       : {result.confidence:.2f}
Why Retrieved    : {result.why_retrieved}
Similarities     :
{similarities}
Potential Overlap: {result.potential_overlap}"""
        )

    return "\n\n".join(lines), len(analyses)


# The base template.  Use build_report_messages() for the recommended entry point.
REPORT_GENERATION_PROMPT: ChatPromptTemplate = ChatPromptTemplate.from_messages(
    [_REPORT_ANALYST_SYSTEM, _REPORT_GENERATION_HUMAN]
)
"""ChatPromptTemplate for the patent landscape report.

Required input variables
------------------------
smiles : str
    SMILES representation of the molecule under review.
disease : str
    Therapeutic disease area being targeted.
target : str
    Biological target of the molecule.
analyses_block : str
    Pre-formatted block of patent analyses produced by
    ``_format_analyses_block()``.
patent_count : int
    Number of patents included in the block.
"""


def build_report_messages(
    smiles: str,
    disease: str,
    target: str,
    analyses: list[tuple[str, object]],
) -> list:
    """Format and return the report-generation prompt as a list of messages.

    This is the recommended entry point for the report generation workflow.
    It handles serialisation of the patent analysis list so callers do not
    need to manage the ``analyses_block`` or ``patent_count`` slots directly.

    Args:
        smiles: SMILES string of the molecule under review.
        disease: Therapeutic disease area (e.g. ``"Pain / Inflammation"``).
        target: Biological target (e.g. ``"COX-2"``).
        analyses: List of ``(patent_title, PatentAnalysisResult)`` tuples.
            Each tuple pairs the human-readable patent title (a ``str``) with
            the corresponding
            :class:`~analysis.schema.PatentAnalysisResult` object.  The list
            may be empty, in which case the prompt will state that no analyses
            are available.

    Returns:
        A list of ``BaseMessage`` objects ready to be passed directly to
        any LangChain chat model (``llm.invoke(messages)``).

    Example::

        from llm.prompts import build_report_messages
        from llm.provider import get_llm

        messages = build_report_messages(
            smiles="CC(=O)Oc1ccccc1C(=O)O",
            disease="Pain / Inflammation",
            target="COX-2",
            analyses=[
                ("Novel aspirin derivatives ...", result_a),
                ("Salicylate compounds for pain ...", result_b),
            ],
        )
        response = get_llm().invoke(messages)
        print(response.content)
    """
    analyses_block, patent_count = _format_analyses_block(analyses)
    return REPORT_GENERATION_PROMPT.format_messages(
        smiles=smiles,
        disease=disease,
        target=target,
        analyses_block=analyses_block,
        patent_count=patent_count,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    # Templates (for advanced use / further composition)
    "PATENT_ANALYSIS_PROMPT",
    "REPORT_GENERATION_PROMPT",
    # Recommended helpers
    "build_patent_analysis_messages",
    "build_report_messages",
    # Internal helper exposed for chain use
    "_build_optional_context",
]
