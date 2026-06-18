"""
Base classes and utilities for NDT data modules.

Each data module should subclass ``BaseNDTData`` and implement the
abstract methods, then expose module-level aliases pointing to its class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldDefinition:
    """Describes a single input field for a tech-card form."""

    name: str
    label: str
    field_type: str = "text"  # text | number | select | textarea | checkbox
    choices: list[tuple[str, str]] = field(default_factory=list)
    required: bool = True
    help_text: str = ""
    default: Any = None
    unit: str = ""


@dataclass
class DefectCriterion:
    """Single row in the quality-acceptance-criteria table."""

    defect_type: str
    parameter: str
    max_allowed: str
    note: str = ""


class BaseNDTData(ABC):
    """Abstract base for all NDT document data modules."""

    DOCUMENT_CODE: str = ""
    DOCUMENT_NAME: str = ""
    METHOD_CODE: str = ""

    @abstractmethod
    def get_card_fields(self) -> list[FieldDefinition]:
        """Return form field definitions for tech-card creation."""

    @abstractmethod
    def generate_card_data(self, input_data: dict) -> dict:
        """
        Process user input and return a dictionary of computed values
        that will be used to fill the DOCX template.
        """

    @abstractmethod
    def get_quality_criteria(self) -> list[DefectCriterion]:
        """Return acceptance criteria table for the quality assessment section."""

    @abstractmethod
    def evaluate_defect(self, defect: dict) -> dict:
        """
        Evaluate a single defect and return:
          {
            'defect_type': str,
            'measured': str,
            'allowable': str,
            'result': 'acceptable' | 'unacceptable',
            'note': str,
          }
        """
