"""
NDT Data package.

Each sub-module corresponds to a specific normative document and exposes:
  - DOCUMENT_CODE: str  — official standard identifier
  - DOCUMENT_NAME: str  — full official name
  - METHOD_CODE: str    — NDTMethod.Code value
  - get_card_fields()   — returns a list of input field definitions
  - generate_card_data(input_data: dict) -> dict  — computed card content
  - get_quality_criteria() -> list  — acceptance criteria table rows
  - evaluate_defect(defect: dict) -> dict  — result for a single defect
"""
