"""Data module for НП-105-18 — Radiographic testing for nuclear power equipment."""

from .base import BaseNDTData, DefectCriterion, FieldDefinition
from .gost_7512 import GOST7512Data

DOCUMENT_CODE = "НП-105-18"
DOCUMENT_NAME = ("Правила контроля металла оборудования и трубопроводов атомных энергетических "
                 "установок при изготовлении и монтаже")
METHOD_CODE = "RT"

EQUIPMENT_GROUPS = [
    ("1", "Группа 1 (реакторная установка)"),
    ("2", "Группа 2 (I контур)"),
    ("3", "Группа 3 (вспомогательные системы)"),
]

WELD_CLASSES = [
    ("I", "Класс I"),
    ("II", "Класс II"),
    ("III", "Класс III"),
]


class NP105Data(BaseNDTData):
    DOCUMENT_CODE = DOCUMENT_CODE
    DOCUMENT_NAME = DOCUMENT_NAME
    METHOD_CODE = METHOD_CODE

    def get_card_fields(self) -> list[FieldDefinition]:
        base = GOST7512Data().get_card_fields()
        extra = [
            FieldDefinition("equipment_group", "Группа оборудования", "select", choices=EQUIPMENT_GROUPS),
            FieldDefinition("weld_class", "Класс сварного соединения", "select", choices=WELD_CLASSES),
            FieldDefinition("object_number", "Номер объекта / узла", "text"),
        ]
        return base + extra

    def generate_card_data(self, input_data: dict) -> dict:
        base_data = GOST7512Data().generate_card_data(input_data)
        weld_class = input_data.get("weld_class", "I")
        group = input_data.get("equipment_group", "1")
        base_data.update({
            "document_code": DOCUMENT_CODE,
            "document_name": DOCUMENT_NAME,
            "required_sensitivity_class": "I" if weld_class == "I" else "II",
            "scope_of_control": "100%" if weld_class in ("I", "II") else "не менее 50%",
            "nuclear_special_requirements": (
                f"Группа оборудования {group}, класс {weld_class}. "
                "Контроль проводится в соответствии с требованиями НП-105-18, Раздел 5."
            ),
            "acceptance_basis": f"{DOCUMENT_CODE}, Приложение 4, Таблица П4.1",
        })
        return base_data

    def get_quality_criteria(self) -> list[DefectCriterion]:
        return [
            DefectCriterion("Трещины", "Все классы", "Не допускаются"),
            DefectCriterion("Округлые поры (класс I)", "Диаметр; кол-во на 100 мм", "≤ 0.5 мм; ≤ 3 шт"),
            DefectCriterion("Округлые поры (класс II)", "Диаметр; кол-во на 100 мм", "≤ 1.0 мм; ≤ 5 шт"),
            DefectCriterion("Шлаковые включения (класс I)", "Длина / ширина", "≤ 1 мм / ≤ 0.5 мм"),
            DefectCriterion("Непровары (класс III)", "Глубина", "≤ 5% толщины, но ≤ 2 мм"),
        ]

    def evaluate_defect(self, defect: dict) -> dict:
        return GOST7512Data().evaluate_defect(defect)


_instance = NP105Data()
get_card_fields = _instance.get_card_fields
generate_card_data = _instance.generate_card_data
get_quality_criteria = _instance.get_quality_criteria
evaluate_defect = _instance.evaluate_defect
