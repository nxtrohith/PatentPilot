"""Patent analysis chain for PatentPilot.

This module wires the patent-analysis prompt template to the Groq LLM using
LangChain's LCEL pipe (``|``) syntax.  Two chain variants are provided:

raw chain (``build_patent_analysis_chain``)
    Returns the LLM's ``AIMessage`` unchanged — useful for debugging or when
    the full narrative text is needed downstream.

structured chain (``build_structured_patent_analysis_chain``)
    Uses LangChain's ``with_structured_output`` to bind the LLM to
    :class:`analysis.schema.PatentAnalysisResult`.  The model populates the
    schema via tool / function calling; no manual JSON parsing is needed.

Typical usage
-------------
::

    from dotenv import load_dotenv
    load_dotenv()

    from chains.patent_analysis import run_structured_patent_analysis, PatentAnalysisInput

    result = run_structured_patent_analysis(
        PatentAnalysisInput(
            smiles="CC(=O)Oc1ccccc1C(=O)O",
            patent_title="Novel salicylate derivatives ...",
            patent_abstract="The present invention relates to ...",
            publication_date="2022-03-10",
            assignee="Pharma Corp Ltd",
            disease="Pain",
            target="COX-2",
        )
    )
    print(result.risk_level)
    print(result.confidence)
    print(result.similarities)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path so this file can be run directly
# (e.g. `uv run chains/patent_analysis.py`) as well as imported as a module.
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dataclasses import dataclass, field
from typing import Optional

from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable
from llm.prompts import PATENT_ANALYSIS_PROMPT, _build_optional_context
from llm.provider import get_llm
from analysis.schema import PatentAnalysisResult


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------


@dataclass
class PatentAnalysisInput:
    """Structured input for the patent analysis chain.

    Attributes:
        smiles: SMILES representation of the compound to analyse.
        patent_title: Title of the patent document.
        patent_abstract: Abstract / summary text of the patent.
        publication_date: Publication or priority date (free-form string,
            e.g. ``"2023-06-15"``).
        assignee: Name of the patent assignee / applicant.
        disease: Optional therapeutic disease area (e.g. ``"Type 2 Diabetes"``).
        target: Optional biological target (e.g. ``"GLP-1 Receptor"``).
    """

    smiles: str
    patent_title: str
    patent_abstract: str
    publication_date: str
    assignee: str
    disease: Optional[str] = field(default=None)
    target: Optional[str] = field(default=None)

    def to_prompt_dict(self) -> dict:
        """Return a dict suitable for passing directly to the prompt template.

        Handles the optional *disease* / *target* fields by generating the
        ``optional_context`` placeholder value expected by
        :data:`llm.prompts.PATENT_ANALYSIS_PROMPT`.
        """
        return {
            "smiles": self.smiles,
            "patent_title": self.patent_title,
            "patent_abstract": self.patent_abstract,
            "publication_date": self.publication_date,
            "assignee": self.assignee,
            "optional_context": _build_optional_context(self.disease, self.target),
        }


# ---------------------------------------------------------------------------
# Raw chain (returns AIMessage)
# ---------------------------------------------------------------------------


def build_patent_analysis_chain(
    model_name: Optional[str] = None,
    temperature: float = 0.0,
) -> Runnable:
    """Build the raw patent analysis LCEL chain.

    The chain is composed as::

        PATENT_ANALYSIS_PROMPT | llm

    It accepts a ``dict`` matching the prompt's input variables (use
    :py:meth:`PatentAnalysisInput.to_prompt_dict`) and returns the raw
    ``AIMessage`` from the model.

    Args:
        model_name: Optional model override forwarded to
            :func:`llm.provider.get_llm`.
        temperature: Sampling temperature. Defaults to ``0.0``.

    Returns:
        A ``Runnable`` (``prompt | llm``) that yields an ``AIMessage``.
    """
    llm = get_llm(model_name=model_name, temperature=temperature)
    return PATENT_ANALYSIS_PROMPT | llm


def run_patent_analysis(
    input_data: PatentAnalysisInput,
    model_name: Optional[str] = None,
    temperature: float = 0.0,
) -> AIMessage:
    """Run the raw patent analysis chain and return the model's ``AIMessage``.

    Args:
        input_data: A :class:`PatentAnalysisInput` with all required fields.
        model_name: Optional model override.
        temperature: Sampling temperature. Defaults to ``0.0``.

    Returns:
        :class:`~langchain_core.messages.AIMessage` — access text via
        ``response.content``.

    Raises:
        ValueError: If ``GROQ_API_KEY`` is not set in the environment.
    """
    chain = build_patent_analysis_chain(
        model_name=model_name,
        temperature=temperature,
    )
    return chain.invoke(input_data.to_prompt_dict())


# ---------------------------------------------------------------------------
# Structured chain (returns PatentAnalysisResult)
# ---------------------------------------------------------------------------


def build_structured_patent_analysis_chain(
    model_name: Optional[str] = None,
    temperature: float = 1.0,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    seed: Optional[int] = None,
) -> Runnable:
    """Build the structured patent analysis LCEL chain.

    Uses LangChain's ``with_structured_output`` to bind the LLM to
    :class:`~analysis.schema.PatentAnalysisResult`.  The model populates the
    Pydantic schema via tool / function calling — no manual JSON parsing is
    required.

    The chain is composed as::

        PATENT_ANALYSIS_PROMPT | llm.with_structured_output(PatentAnalysisResult)

    Args:
        model_name: Optional model override forwarded to
            :func:`llm.provider.get_llm`.
        temperature: Sampling temperature. Defaults to ``1.0`` to match
            GLM-5.2's recommended setting.
        top_p: Nucleus-sampling probability mass (NVIDIA/GLM only).
        max_tokens: Maximum completion tokens (NVIDIA/GLM only).
        seed: Fixed random seed (NVIDIA/GLM only).

    Returns:
        A ``Runnable`` that yields a :class:`~analysis.schema.PatentAnalysisResult`
        Pydantic object directly.

    Example::

        chain = build_structured_patent_analysis_chain()
        result: PatentAnalysisResult = chain.invoke(input_obj.to_prompt_dict())
        print(result.risk_level)   # e.g. RiskLevel.HIGH
        print(result.confidence)   # e.g. 0.82
    """
    llm = get_llm(
        model_name=model_name,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        seed=seed,
    )
    structured_llm = llm.with_structured_output(PatentAnalysisResult)
    return PATENT_ANALYSIS_PROMPT | structured_llm


def run_structured_patent_analysis(
    input_data: PatentAnalysisInput,
    model_name: Optional[str] = None,
    temperature: float = 0.0,
) -> PatentAnalysisResult:
    """Run the structured patent analysis chain and return a Pydantic result.

    This is the recommended entry point for production use.  The LLM populates
    :class:`~analysis.schema.PatentAnalysisResult` directly via tool calling;
    no manual parsing is performed.

    Args:
        input_data: A :class:`PatentAnalysisInput` with all required fields.
        model_name: Optional model override.
        temperature: Sampling temperature. Defaults to ``0.0``.

    Returns:
        :class:`~analysis.schema.PatentAnalysisResult` — a validated Pydantic
        object containing ``why_retrieved``, ``similarities``,
        ``potential_overlap``, ``confidence``, and ``risk_level``.

    Raises:
        ValueError: If ``GROQ_API_KEY`` is not set in the environment.
    """
    chain = build_structured_patent_analysis_chain(
        model_name=model_name,
        temperature=temperature,
    )
    return chain.invoke(input_data.to_prompt_dict())


# ---------------------------------------------------------------------------
# Test / smoke-test entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os

    from dotenv import load_dotenv
    load_dotenv()

    print("=" * 60)
    print("PatentPilot — structured patent analysis chain test")
    print("=" * 60)

    sample_input = PatentAnalysisInput(
        smiles="CC(=O)Oc1ccccc1C(=O)O",
        patent_title="Novel aspirin-derived compounds for anti-inflammatory therapy",
        patent_abstract=(
            "The present invention discloses novel acetylsalicylic acid derivatives "
            "exhibiting enhanced COX-2 selectivity and improved gastrointestinal "
            "tolerability compared to the parent compound aspirin. The compounds "
            "are useful in the treatment of pain, fever, and inflammatory disorders."
        ),
        publication_date="2022-03-10",
        assignee="Pharma Corp Ltd",
        disease="Pain / Inflammation",
        target="COX-2",
    )

    print("\nInput:")
    print(f"  SMILES       : {sample_input.smiles}")
    print(f"  Title        : {sample_input.patent_title}")
    print(f"  Assignee     : {sample_input.assignee}")
    print(f"  Disease      : {sample_input.disease}")
    print(f"  Target       : {sample_input.target}")

    print("\nRunning structured analysis…")
    try:
        result: PatentAnalysisResult = run_structured_patent_analysis(sample_input)

        print("\n" + "=" * 60)
        print("Dashboard Analysis (Structured)")
        print("=" * 60)
        print(f"\nWhy Retrieved    : {result.why_retrieved}")
        print(f"\nSimilarities     :")
        for i, s in enumerate(result.similarities, 1):
            print(f"  {i}. {s}")
        print(f"\nPotential Overlap: {result.potential_overlap}")
        print(f"\nConfidence       : {result.confidence:.2f}")
        print(f"Risk Level       : {result.risk_level.value.upper()}")
        print("=" * 60)

    except ValueError as exc:
        print(f"\n[ERROR] {exc}")
        print("Make sure GROQ_API_KEY is set in your .env file.")
    except Exception as exc:
        print(f"\n[ERROR] Unexpected error: {exc}")
        raise
