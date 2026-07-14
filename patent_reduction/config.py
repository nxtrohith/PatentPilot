"""Configuration for the patent reduction pipeline.

Every threshold and weight referenced in the reduction/ranking spec lives
here so behaviour can be tuned without touching logic code. Config can be
constructed directly, or loaded from a JSON file via ``ReductionConfig.load``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# Country priority used when picking a representative patent for a family.
# Lower index = higher priority. Anything not listed falls back to
# ``DEFAULT_COUNTRY_PRIORITY``.
DEFAULT_FAMILY_COUNTRY_PRIORITY = ("WO", "US", "EP", "JP", "CN")
DEFAULT_COUNTRY_PRIORITY_FALLBACK = 999


@dataclass
class StructuralScoreConfig:
    """Normalizes SureChEMBL similarity (0-1) into a 0-100 score."""

    neutral_default_score: float = 50.0


@dataclass
class ChemicalEvidenceScoreConfig:
    """Weights for the evidence-count metrics, and the cap used to normalize."""

    matched_chemicals_weight: float = 1.0
    annotations_weight: float = 0.5
    chemical_ids_weight: float = 0.5
    # Raw weighted count that maps to a full 100 score. Counts above this
    # are clamped to 100.
    max_evidence_for_full_score: float = 10.0


@dataclass
class ClaimImportanceScoreConfig:
    """Section weights used to score where matched chemicals occur."""

    claims_weight: float = 100.0
    abstract_weight: float = 70.0
    title_weight: float = 50.0
    description_weight: float = 20.0

    @property
    def max_possible(self) -> float:
        return (
            self.claims_weight
            + self.abstract_weight
            + self.title_weight
            + self.description_weight
        )


@dataclass
class LegalStatusScoreConfig:
    """Point deltas applied per legal-status keyword (case-insensitive)."""

    status_points: Dict[str, float] = field(
        default_factory=lambda: {
            "granted": 20.0,
            "published": 15.0,
            "pending": 15.0,
            "expired": -15.0,
            "rejected": -25.0,
            "withdrawn": -30.0,
            "lapsed": -20.0,
        }
    )
    unknown_status_score: float = 0.0
    # Clamp bounds for the raw legal score.
    min_score: float = -30.0
    max_score: float = 20.0


@dataclass
class RecencyScoreConfig:
    """Age-bucket bonuses based on years since publication."""

    # (max_years_inclusive, score) evaluated in order; first match wins.
    buckets: tuple = (
        (5, 20.0),
        (10, 10.0),
        (20, 5.0),
    )
    older_score: float = 0.0
    unknown_date_score: float = 0.0


@dataclass
class CompositeWeights:
    """Weights (should sum to 1.0) for the final composite score."""

    structure: float = 0.40
    chemical_evidence: float = 0.20
    claim_importance: float = 0.20
    legal: float = 0.10
    recency: float = 0.10


@dataclass
class FilterConfig:
    """Post-ranking filtering limits."""

    max_patents: int = 20
    min_score: float = 55.0


@dataclass
class FamilyConfig:
    """Family-collapse representative-selection preferences."""

    country_priority: tuple = DEFAULT_FAMILY_COUNTRY_PRIORITY
    fallback_priority: int = DEFAULT_COUNTRY_PRIORITY_FALLBACK


@dataclass
class ReductionConfig:
    """Top-level configuration for :class:`PatentReductionPipeline`."""

    family: FamilyConfig = field(default_factory=FamilyConfig)
    structural: StructuralScoreConfig = field(default_factory=StructuralScoreConfig)
    chemical_evidence: ChemicalEvidenceScoreConfig = field(
        default_factory=ChemicalEvidenceScoreConfig
    )
    claim_importance: ClaimImportanceScoreConfig = field(
        default_factory=ClaimImportanceScoreConfig
    )
    legal: LegalStatusScoreConfig = field(default_factory=LegalStatusScoreConfig)
    recency: RecencyScoreConfig = field(default_factory=RecencyScoreConfig)
    weights: CompositeWeights = field(default_factory=CompositeWeights)
    filters: FilterConfig = field(default_factory=FilterConfig)

    @classmethod
    def load(cls, path: Optional[str]) -> "ReductionConfig":
        """Load config from a JSON file, falling back to defaults.

        Any keys not present in the file simply keep their default values,
        so partial config files are valid.
        """
        if path is None:
            return cls()
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw: Dict[str, Any] = json.load(fh)
        except FileNotFoundError:
            logger.warning("Config file %s not found; using defaults.", path)
            return cls()
        except json.JSONDecodeError as exc:
            logger.warning("Config file %s is invalid JSON (%s); using defaults.", path, exc)
            return cls()

        config = cls()
        for section_name in (
            "family",
            "structural",
            "chemical_evidence",
            "claim_importance",
            "legal",
            "recency",
            "weights",
            "filters",
        ):
            section_data = raw.get(section_name)
            if not isinstance(section_data, dict):
                continue
            section_obj = getattr(config, section_name)
            for key, value in section_data.items():
                if hasattr(section_obj, key):
                    setattr(section_obj, key, value)
                else:
                    logger.warning("Unknown config key %s.%s ignored.", section_name, key)
        return config

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
