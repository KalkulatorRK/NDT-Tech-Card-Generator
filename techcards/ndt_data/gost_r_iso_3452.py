"""Data module for ГОСТ Р ИСО 3452-1-2011 — Liquid penetrant testing."""

from .base import BaseNDTData, DefectCriterion, FieldDefinition

DOCUMENT_CODE = "ГОСТ Р ИСО 3452-1-2011"
DOCUMENT_NAME = "Неразрушающий контроль. Капиллярный контроль. Часть 1. Основные требования."
METHOD_CODE = "PT"

PENETRANT_SYSTEMS = [
    ("type_I_A", "Тип I метод A (флуоресцентный, водосмываемый)"),
    ("type_I_B", "Тип I метод B (флуоресцентный, на основе растворителя)"),
    ("type_I_C", "Тип I метод C (флуоресцентный, эмульгируемый)"),
    ("type_II_A", "Тип II метод A (цветной, водосмываемый)"),
    ("type_II_B", "Тип II метод B (цветной, на основе растворителя)"),
    ("type_II_C", "Тип II метод C (цветной, эмульгируемый)"),
]

PENETRANT_DWELL_TIMES = {
    "steel_carbon": 10,
    "steel_stainless": 10,
    "aluminum": 5,
    "titanium": 20,
    "nickel": 15,
}

SENSITIVITY_LEVELS = [
    ("1", "Уровень чувствительности 1 (низкий)"),
    ("2", "Уровень чувствительности 2 (средний)"),
    ("3", "Уровень чувствительности 3 (высокий)"),
    ("4", "Уровень чувствительности 4 (ультравысокий)"),
]


class GOST3452Data(BaseNDTData):
    DOCUMENT_CODE = DOCUMENT_CODE
    DOCUMENT_NAME = DOCUMENT_NAME
    METHOD_CODE = METHOD_CODE

    def get_card_fields(self) -> list[FieldDefinition]:
        return [
            FieldDefinition("object_type", "Тип объекта контроля", "text"),
            FieldDefinition("material", "Материал объекта", "select",
                choices=[
                    ("steel_carbon", "Сталь углеродистая / низколегированная"),
                    ("steel_stainless", "Сталь высоколегированная / нержавеющая"),
                    ("aluminum", "Алюминиевые сплавы"),
                    ("titanium", "Титановые сплавы"),
                    ("nickel", "Никелевые сплавы"),
                ]),
            FieldDefinition("penetrant_system", "Система пенетрантов", "select", choices=PENETRANT_SYSTEMS),
            FieldDefinition("sensitivity_level", "Уровень чувствительности", "select", choices=SENSITIVITY_LEVELS),
            FieldDefinition("surface_condition", "Состояние поверхности", "select",
                choices=[
                    ("machined", "Механически обработанная"),
                    ("as_welded", "Необработанная (после сварки)"),
                    ("ground", "Шлифованная"),
                ]),
            FieldDefinition("temperature_c", "Температура контролируемой поверхности", "number", unit="°C", default=20),
            FieldDefinition("nk_specialist", "Специалист НК (ФИО, уровень квалификации)", "text"),
        ]

    def generate_card_data(self, input_data: dict) -> dict:
        material = input_data.get("material", "steel_carbon")
        dwell_time = PENETRANT_DWELL_TIMES.get(material, 10)
        temperature = float(input_data.get("temperature_c", 20))

        if temperature < 10 or temperature > 50:
            temp_note = "ВНИМАНИЕ: температура вне стандартного диапазона (+10…+50°С). Требуется специальная процедура."
        else:
            temp_note = "Температура в допустимом диапазоне."

        return {
            **input_data,
            "document_code": DOCUMENT_CODE,
            "document_name": DOCUMENT_NAME,
            "penetrant_dwell_time_min": dwell_time,
            "developer_dwell_time_min": 10,
            "surface_preparation": "Очистить поверхность от загрязнений, обезжирить ацетоном или спиртом",
            "penetrant_application": "Нанести проникающий пенетрант методом напыления или кистью",
            "excess_removal": "Удалить излишки пенетранта протиркой или промывкой",
            "developer_application": "Нанести тонкий равномерный слой проявителя",
            "inspection_time_min": 10,
            "uv_lamp_required": "Да" if "type_I" in input_data.get("penetrant_system", "type_II_B") else "Нет",
            "temperature_note": temp_note,
            "acceptance_basis": f"{DOCUMENT_CODE}, Таблица 1",
        }

    def get_quality_criteria(self) -> list[DefectCriterion]:
        return [
            DefectCriterion("Трещины", "Все уровни чувствительности", "Не допускаются"),
            DefectCriterion("Линейные индикации", "Уровень 2: длина", "≤ 2 мм"),
            DefectCriterion("Линейные индикации", "Уровень 3: длина", "≤ 1 мм"),
            DefectCriterion("Округлые индикации", "Уровень 2: диаметр", "≤ 4 мм"),
            DefectCriterion("Округлые индикации", "Уровень 3: диаметр", "≤ 2 мм"),
            DefectCriterion("Скопления пор", "Уровень 2", "≤ 4 индикации на 100 мм²"),
        ]

    def evaluate_defect(self, defect: dict) -> dict:
        defect_type = defect.get("defect_type", "")
        size_mm = float(defect.get("size_mm", 0))
        level = int(defect.get("sensitivity_level", 2))

        if defect_type in ("crack", "Трещина", "linear", "Линейная индикация"):
            if defect_type in ("crack", "Трещина"):
                return {"defect_type": defect_type, "measured": f"{size_mm}", "allowable": "0", "result": "unacceptable", "note": "Трещины не допускаются"}
            max_len = {2: 2.0, 3: 1.0}.get(level, 2.0)
            result = "acceptable" if size_mm <= max_len else "unacceptable"
            return {"defect_type": defect_type, "measured": f"{size_mm} мм", "allowable": f"≤ {max_len} мм", "result": result, "note": f"Уровень {level}"}

        max_dia = {2: 4.0, 3: 2.0}.get(level, 4.0)
        result = "acceptable" if size_mm <= max_dia else "unacceptable"
        return {"defect_type": defect_type, "measured": f"{size_mm} мм", "allowable": f"≤ {max_dia} мм", "result": result, "note": f"Уровень {level}"}


_instance = GOST3452Data()
get_card_fields = _instance.get_card_fields
generate_card_data = _instance.generate_card_data
get_quality_criteria = _instance.get_quality_criteria
evaluate_defect = _instance.evaluate_defect
