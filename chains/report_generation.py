"""Report generation chain for PatentPilot.

This module wires the report generation prompt template to the LLM using
LangChain's LCEL pipe (``|``) syntax.

structured chain (``build_structured_report_generation_chain``)
    Uses LangChain's ``with_structured_output`` to bind the LLM to
    :class:`analysis.schema.PatentReportResult`.  The model populates the
    schema via tool / function calling; no manual JSON parsing is needed.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path so this file can be run directly
_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dataclasses import dataclass, field
from typing import Optional

from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.language_models.chat_models import BaseChatModel
from llm.prompts import build_report_messages
from analysis.schema import PatentReportResult, PatentAnalysisResult


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------


@dataclass
class ReportGenerationInput:
    """Structured input for the report generation chain.

    Attributes:
        smiles: SMILES string of the molecule under review.
        disease: Therapeutic disease area (e.g. ``"Pain / Inflammation"``).
        target: Biological target (e.g. ``"COX-2"``).
        analyses: List of tuples pairing the patent title with its
            :class:`~analysis.schema.PatentAnalysisResult`.
    """

    smiles: str
    disease: str
    target: str
    analyses: list[tuple[str, PatentAnalysisResult]] = field(default_factory=list)

    def to_messages(self) -> list:
        """Format the input as a list of LLM messages."""
        return build_report_messages(
            smiles=self.smiles,
            disease=self.disease,
            target=self.target,
            analyses=self.analyses,
        )


# ---------------------------------------------------------------------------
# Structured chain (returns PatentReportResult)
# ---------------------------------------------------------------------------


def build_structured_report_generation_chain(
    llm: BaseChatModel,
) -> Runnable:
    """Build the structured report generation LCEL chain.

    Uses LangChain's ``with_structured_output`` to bind the LLM to
    :class:`~analysis.schema.PatentReportResult`.  The model populates the
    Pydantic schema via tool / function calling.

    Args:
        llm: A configured LangChain chat model.

    Returns:
        A ``Runnable`` that takes a :class:`ReportGenerationInput` and yields a
        :class:`~analysis.schema.PatentReportResult` Pydantic object directly.
    """
    structured_llm = llm.with_structured_output(PatentReportResult)

    return RunnableLambda(lambda x: x.to_messages()) | structured_llm


def run_structured_report_generation(
    input_data: ReportGenerationInput,
    llm: BaseChatModel,
) -> PatentReportResult:
    """Run the structured report generation chain and return a Pydantic result.

    This is the recommended entry point for generating the final landscape report.

    Args:
        input_data: A :class:`ReportGenerationInput` with all required fields.
        llm: A configured LangChain chat model.

    Returns:
        :class:`~analysis.schema.PatentReportResult` — a validated Pydantic
        object containing the overall recommendation and report details.
    """
    chain = build_structured_report_generation_chain(llm)
    return chain.invoke(input_data)  # type: ignore


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "ReportGenerationInput",
    "build_structured_report_generation_chain",
    "run_structured_report_generation",
]
