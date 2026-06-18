"""Data module for ГОСТ Р ИСО 17637-2014 — Visual testing of fusion-welded joints."""

from .base import BaseNDTData, DefectCriterion, FieldDefinition

DOCUMENT_CODE = "ГОСТ Р ИСО 17637-2014"
DOCUMENT_NAME = "Неразрушающий контроль сварных соединений. Визуальный контроль сварных соединений, выполненных сваркой плавлением."
METHOD_CODE = "VT"

ACCEPTANCE_LEVELS = [
    ("B", "Уровень B (умеренный)"),
    ("C", "Уровень C (средний)"),
    ("D", "Уровень D (мягкий)"),
]

DEFECT_NORMS = {
    "B": {
        "undercut": 0.5,
        "misalignment": 0.25,  # fraction of thickness
        "reinforcement": 1.0,
    },
    "C": {
        "undercut": 1.0,
        "misalignment": 0.5,
        "reinforcement": 2.0,
    },
    "D": {
        "undercut": 2.0,
        "misalignment": 1.0,
        "reinforcement": 4.0,
    },
}


class GOST17637Data(BaseNDTData):
    DOCUMENT_CODE = DOCUMENT_CODE
    DOCUMENT_NAME = DOCUMENT_NAME
    METHOD_CODE = METHOD_CODE

    def get_card_fields(self) -> list[FieldDefinition]:
        return [
            FieldDefinition("object_type", "Тип объекта", "text"),
            FieldDefinition("material", "Материал", "text"),
            FieldDefinition("thickness_mm", "Толщина металла, мм", "number", unit="мм"),
            FieldDefinition(
                "acceptance_level",
                "Уровень приёмки",
                "select",
                choices=ACCEPTANCE_LEVELS,
            ),
            FieldDefinition("nk_specialist", "Специалист НК", "text"),
        ]

    def generate_card_data(self, input_data: dict) -> dict:
        level = input_data.get("acceptance_level", "C")
        norms = DEFECT_NORMS.get(level, DEFECT_NORMS["C"])
        thickness = float(input_data.get("thickness_mm", 10))
        return {
            **input_data,
            "document_code": DOCUMENT_CODE,
            "document_name": DOCUMENT_NAME,
            "allowable_undercut_mm": norms["undercut"],
            "allowable_misalignment_mm": round(norms["misalignment"] * thickness, 2),
            "allowable_reinforcement_mm": norms["reinforcement"],
            "cracks_allowed": "Не допускаются (уровни B, C, D)",
            "acceptance_basis": f"{DOCUMENT_CODE}, Таблица 1, уровень {level}",
        }

    def get_quality_criteria(self) -> list[DefectCriterion]:
        criteria = []
        for level, norms in DEFECT_NORMS.items():
            criteria += [
                DefectCriterion("Подрез", f"Уровень {level}: глубина", f"≤ {norms['undercut']} мм"),
                DefectCriterion("Выпуклость", f"Уровень {level}: высота", f"≤ {norms['reinforcement']} мм"),
            ]
        criteria.append(DefectCriterion("Трещины", "Все уровни", "Не допускаются"))
        return criteria

    def evaluate_defect(self, defect: dict) -> dict:
        level = defect.get("acceptance_level", "C")
        defect_type = defect.get("defect_type", "")
        size_mm = float(defect.get("size_mm", 0))
        norms = DEFECT_NORMS.get(level, DEFECT_NORMS["C"])

        if defect_type in ("crack", "Трещина"):
            return {"defect_type": defect_type, "measured": f"{size_mm}", "allowable": "0", "result": "unacceptable", "note": "Трещины не допускаются"}

        norm_map = {"undercut": "undercut", "Подрез": "undercut", "reinforcement": "reinforcement", "Выпуклость": "reinforcement"}
        if defect_type in norm_map:
            key = norm_map[defect_type]
            allowed = norms[key]
            return {
                "defect_type": defect_type,
                "measured": f"{size_mm} мм",
                "allowable": f"≤ {allowed} мм",
                "result": "acceptable" if size_mm <= allowed else "unacceptable",
                "note": f"Уровень {level}",
            }
        return {"defect_type": defect_type, "measured": f"{size_mm}", "allowable": "—", "result": "requires_review", "note": ""}


_instance = GOST17637Data()
get_card_fields = _instance.get_card_fields
generate_card_data = _instance.generate_card_data
get_quality_criteria = _instance.get_quality_criteria
evaluate_defect = _instance.evaluate_defect
