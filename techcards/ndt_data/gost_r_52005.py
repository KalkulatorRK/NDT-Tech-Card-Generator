"""Data module for ГОСТ Р 52005-2003 — Leak testing."""

from .base import BaseNDTData, DefectCriterion, FieldDefinition

DOCUMENT_CODE = "ГОСТ Р 52005-2003"
DOCUMENT_NAME = "Контроль неразрушающий. Метод течеискания. Общие требования."
METHOD_CODE = "LT"

LEAK_TEST_METHODS = [
    ("pneumatic", "Пневматический (воздух/азот)"),
    ("hydraulic", "Гидравлический (вода)"),
    ("vacuum", "Вакуумный"),
    ("helium", "Гелиевый течеискатель"),
    ("ammonia", "Аммиачный"),
]

LEAK_CATEGORIES = [
    ("A", "Категория A (высоконапорные, опасные)"),
    ("B", "Категория B (среднее давление)"),
    ("C", "Категория C (низкое давление)"),
]


class GOST52005Data(BaseNDTData):
    DOCUMENT_CODE = DOCUMENT_CODE
    DOCUMENT_NAME = DOCUMENT_NAME
    METHOD_CODE = METHOD_CODE

    def get_card_fields(self) -> list[FieldDefinition]:
        return [
            FieldDefinition("object_type", "Тип объекта контроля", "text"),
            FieldDefinition("working_medium", "Рабочая среда", "text", help_text="Например: природный газ, горячая вода, пар"),
            FieldDefinition("test_method", "Метод контроля герметичности", "select", choices=LEAK_TEST_METHODS),
            FieldDefinition("test_pressure_mpa", "Испытательное давление", "number", unit="МПа"),
            FieldDefinition("holding_time_min", "Время выдержки под давлением", "number", unit="мин", default=30),
            FieldDefinition("leak_category", "Категория контроля герметичности", "select", choices=LEAK_CATEGORIES),
            FieldDefinition("temperature_c", "Температура испытательной среды", "number", unit="°C", default=20),
            FieldDefinition("nk_specialist", "Специалист НК (ФИО, уровень квалификации)", "text"),
        ]

    def generate_card_data(self, input_data: dict) -> dict:
        method = input_data.get("test_method", "pneumatic")
        pressure = float(input_data.get("test_pressure_mpa", 0.6))
        holding = int(input_data.get("holding_time_min", 30))
        category = input_data.get("leak_category", "B")

        sensitivity_map = {
            "A": "Класс 1 (≤ 1×10⁻³ Па·м³/с)",
            "B": "Класс 2 (≤ 1×10⁻² Па·м³/с)",
            "C": "Класс 3 (≤ 1×10⁻¹ Па·м³/с)",
        }

        return {
            **input_data,
            "document_code": DOCUMENT_CODE,
            "document_name": DOCUMENT_NAME,
            "required_sensitivity": sensitivity_map.get(category, sensitivity_map["B"]),
            "pre_inspection_check": "Проверить целостность объекта, установить заглушки и манометры",
            "pressure_raise_rate": "Плавное повышение давления со скоростью не более 0.1 МПа/мин",
            "acceptance_criterion": "Отсутствие падения давления более 0.1% за время выдержки; отсутствие пузырей и мыльных плёнок",
            "documentation": "Акт испытания на герметичность по форме приложения к ГОСТ Р 52005",
            "acceptance_basis": f"{DOCUMENT_CODE}, раздел 5",
        }

    def get_quality_criteria(self) -> list[DefectCriterion]:
        return [
            DefectCriterion("Падение давления", "Категория A: за время выдержки", "≤ 0.05%"),
            DefectCriterion("Падение давления", "Категория B: за время выдержки", "≤ 0.1%"),
            DefectCriterion("Падение давления", "Категория C: за время выдержки", "≤ 0.5%"),
            DefectCriterion("Видимые течи", "Все категории", "Не допускаются"),
            DefectCriterion("Пузырение при обмыливании", "Все категории", "Не допускается"),
        ]

    def evaluate_defect(self, defect: dict) -> dict:
        defect_type = defect.get("defect_type", "")
        category = defect.get("leak_category", "B")
        pressure_drop_pct = float(defect.get("pressure_drop_pct", 0))

        allowed_map = {"A": 0.05, "B": 0.1, "C": 0.5}
        allowed = allowed_map.get(category, 0.1)

        if defect_type in ("visible_leak", "Видимая течь", "bubbles", "Пузырение"):
            return {"defect_type": defect_type, "measured": "зафиксировано", "allowable": "Не допускается", "result": "unacceptable", "note": ""}
        if defect_type in ("pressure_drop", "Падение давления"):
            result = "acceptable" if pressure_drop_pct <= allowed else "unacceptable"
            return {"defect_type": defect_type, "measured": f"{pressure_drop_pct}%", "allowable": f"≤ {allowed}%", "result": result, "note": f"Категория {category}"}

        return {"defect_type": defect_type, "measured": "", "allowable": "—", "result": "requires_review", "note": ""}


_instance = GOST52005Data()
get_card_fields = _instance.get_card_fields
generate_card_data = _instance.generate_card_data
get_quality_criteria = _instance.get_quality_criteria
evaluate_defect = _instance.evaluate_defect
