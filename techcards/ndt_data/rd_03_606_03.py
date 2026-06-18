"""
Data module for РД 03-606-03 — Visual and Measurement Testing (ВИК).

Содержит:
  - Поля ввода для технологической карты ВИК
  - Данные нормативных таблиц (допускаемые размеры дефектов)
  - Логику оценки дефектов
"""

from .base import BaseNDTData, DefectCriterion, FieldDefinition

DOCUMENT_CODE = "РД 03-606-03"
DOCUMENT_NAME = "Инструкция по визуальному и измерительному контролю"
METHOD_CODE = "VT"

WELD_TYPES = [
    ("butt", "Стыковое соединение"),
    ("fillet", "Угловое соединение"),
    ("overlap", "Нахлёсточное соединение"),
    ("tee", "Тавровое соединение"),
]

MATERIAL_TYPES = [
    ("steel_carbon", "Углеродистая и низколегированная сталь"),
    ("steel_alloy", "Легированная сталь (кроме высоколегированной)"),
    ("steel_stainless", "Высоколегированная коррозионностойкая сталь"),
    ("aluminum", "Алюминий и алюминиевые сплавы"),
    ("titanium", "Титан и титановые сплавы"),
]

WELD_CATEGORIES = [
    ("I", "Категория I (ответственные)"),
    ("II", "Категория II"),
    ("III", "Категория III (рядовые)"),
]

CONTROL_STAGES = [
    ("incoming", "Входной контроль"),
    ("in_process", "Контроль в процессе сварки"),
    ("final", "Приёмочный контроль"),
    ("all", "Входной + в процессе + приёмочный"),
]

# Таблица допускаемых несплошностей по РД 03-606-03
# (размеры в мм, для стыковых швов)
DEFECT_NORMS = {
    "I": {
        "undercut_depth_max": 0.1,  # подрез, глубина
        "surface_pore_dia_max": 0.5,  # поверхностные поры, диаметр
        "root_sag_max": 0.5,  # превышение проплавления (вогнутость корня)
        "reinforcement_height_max": 2.0,  # выпуклость шва
        "angular_misalignment_max": 1.0,  # угловое смещение, мм
        "linear_misalignment_max": 0.5,  # линейное смещение
    },
    "II": {
        "undercut_depth_max": 0.2,
        "surface_pore_dia_max": 1.0,
        "root_sag_max": 1.0,
        "reinforcement_height_max": 3.0,
        "angular_misalignment_max": 2.0,
        "linear_misalignment_max": 1.0,
    },
    "III": {
        "undercut_depth_max": 0.5,
        "surface_pore_dia_max": 2.0,
        "root_sag_max": 1.5,
        "reinforcement_height_max": 4.0,
        "angular_misalignment_max": 3.0,
        "linear_misalignment_max": 2.0,
    },
}

DEFECT_TYPE_CHOICES = [
    ("undercut", "Подрез"),
    ("surface_pore", "Поверхностная пора"),
    ("crack", "Трещина"),
    ("root_sag", "Вогнутость корня"),
    ("reinforcement", "Выпуклость шва"),
    ("angular_misalignment", "Угловое смещение"),
    ("linear_misalignment", "Линейное смещение"),
    ("burn_through", "Прожог"),
    ("crater", "Кратер"),
    ("other", "Прочее"),
]


class RD03606Data(BaseNDTData):
    DOCUMENT_CODE = DOCUMENT_CODE
    DOCUMENT_NAME = DOCUMENT_NAME
    METHOD_CODE = METHOD_CODE

    def get_card_fields(self) -> list[FieldDefinition]:
        return [
            FieldDefinition(
                name="object_type",
                label="Тип объекта контроля",
                field_type="select",
                choices=[
                    ("pipe", "Трубопровод"),
                    ("vessel", "Сосуд давления"),
                    ("structure", "Металлоконструкция"),
                    ("tank", "Резервуар"),
                    ("other", "Прочее"),
                ],
            ),
            FieldDefinition(
                name="object_dimensions",
                label="Типоразмер и размеры объекта",
                field_type="text",
                help_text="Например: труба Ø 89×4 мм, длина 600 мм",
            ),
            FieldDefinition(
                name="material",
                label="Марка материала",
                field_type="select",
                choices=MATERIAL_TYPES,
            ),
            FieldDefinition(
                name="weld_type",
                label="Тип сварного соединения",
                field_type="select",
                choices=WELD_TYPES,
            ),
            FieldDefinition(
                name="thickness_mm",
                label="Толщина основного металла",
                field_type="number",
                unit="мм",
            ),
            FieldDefinition(
                name="weld_category",
                label="Категория сварного шва",
                field_type="select",
                choices=WELD_CATEGORIES,
            ),
            FieldDefinition(
                name="control_stage",
                label="Стадия контроля",
                field_type="select",
                choices=CONTROL_STAGES,
            ),
            FieldDefinition(
                name="welding_method",
                label="Метод сварки",
                field_type="select",
                choices=[
                    ("manual_arc", "Ручная дуговая (РД)"),
                    ("tig", "Аргонодуговая (ТИГ/РАД)"),
                    ("mig_mag", "Полуавтоматическая (МИГ/МАГ)"),
                    ("submerged", "Под флюсом (АФ)"),
                    ("plasma", "Плазменная"),
                    ("laser", "Лазерная"),
                    ("gas", "Газовая"),
                    ("other", "Прочее"),
                ],
            ),
            FieldDefinition(
                name="control_tools",
                label="Средства контроля (приборы, инструменты)",
                field_type="textarea",
                help_text="Перечислите применяемые инструменты: линейки, угольники, шаблоны УШС и т.д.",
                required=False,
            ),
            FieldDefinition(
                name="illumination_lux",
                label="Освещённость контролируемой поверхности",
                field_type="number",
                unit="лк",
                default=500,
                help_text="Не менее 500 лк согласно РД 03-606-03",
            ),
            FieldDefinition(
                name="nk_specialist",
                label="Специалист НК (ФИО, уровень квалификации)",
                field_type="text",
            ),
        ]

    def generate_card_data(self, input_data: dict) -> dict:
        weld_category = input_data.get("weld_category", "III")
        thickness = float(input_data.get("thickness_mm", 10))
        norms = DEFECT_NORMS.get(weld_category, DEFECT_NORMS["III"])

        return {
            **input_data,
            "document_code": DOCUMENT_CODE,
            "document_name": DOCUMENT_NAME,
            "scope_of_control": "100% сварных швов",
            "preparation": (
                "Поверхность очистить от шлака, брызг, окалины. "
                "Ширина зачистки — не менее 20 мм от оси шва с каждой стороны."
            ),
            "min_illumination_lux": 500,
            "required_surface_condition": "Без механических повреждений, чистая",
            "allowable_undercut_depth_mm": norms["undercut_depth_max"],
            "allowable_pore_dia_mm": norms["surface_pore_dia_max"],
            "allowable_root_sag_mm": norms["root_sag_max"],
            "allowable_reinforcement_mm": norms["reinforcement_height_max"],
            "allowable_linear_misalignment_mm": norms["linear_misalignment_max"],
            "cracks_allowed": "Не допускаются",
            "burn_through_allowed": "Не допускаются",
            "acceptance_basis": f"{DOCUMENT_CODE}, Приложение 1, Таблица 1",
        }

    def get_quality_criteria(self) -> list[DefectCriterion]:
        criteria = []
        for cat, norms in DEFECT_NORMS.items():
            criteria += [
                DefectCriterion(
                    defect_type="Подрез",
                    parameter=f"Категория {cat}: глубина",
                    max_allowed=f"≤ {norms['undercut_depth_max']} мм",
                    note="РД 03-606-03, Приложение 1",
                ),
                DefectCriterion(
                    defect_type="Поверхностная пора",
                    parameter=f"Категория {cat}: диаметр",
                    max_allowed=f"≤ {norms['surface_pore_dia_max']} мм",
                    note="РД 03-606-03, Приложение 1",
                ),
                DefectCriterion(
                    defect_type="Выпуклость шва",
                    parameter=f"Категория {cat}: высота",
                    max_allowed=f"≤ {norms['reinforcement_height_max']} мм",
                    note="РД 03-606-03",
                ),
            ]
        criteria.append(
            DefectCriterion(
                defect_type="Трещины",
                parameter="Все категории",
                max_allowed="Не допускаются",
                note="РД 03-606-03, п.5.2",
            )
        )
        return criteria

    def evaluate_defect(self, defect: dict) -> dict:
        defect_type = defect.get("defect_type", "")
        weld_category = defect.get("weld_category", "III")
        size_mm = float(defect.get("size_mm", 0))
        norms = DEFECT_NORMS.get(weld_category, DEFECT_NORMS["III"])

        not_allowed = ("crack", "Трещина", "burn_through", "Прожог", "crater", "Кратер")
        if defect_type in not_allowed:
            return {
                "defect_type": defect_type,
                "measured": f"{size_mm} мм",
                "allowable": "Не допускается",
                "result": "unacceptable",
                "note": f"РД 03-606-03, категория {weld_category}",
            }

        norm_map = {
            "undercut": ("undercut_depth_max", "Подрез: глубина"),
            "Подрез": ("undercut_depth_max", "Подрез: глубина"),
            "surface_pore": ("surface_pore_dia_max", "Поверхностная пора: диаметр"),
            "Поверхностная пора": ("surface_pore_dia_max", "Поверхностная пора: диаметр"),
            "root_sag": ("root_sag_max", "Вогнутость корня"),
            "reinforcement": ("reinforcement_height_max", "Выпуклость шва"),
            "linear_misalignment": ("linear_misalignment_max", "Линейное смещение"),
        }

        if defect_type in norm_map:
            key, label = norm_map[defect_type]
            allowable = norms[key]
            result = "acceptable" if size_mm <= allowable else "unacceptable"
            return {
                "defect_type": defect_type,
                "measured": f"{size_mm} мм",
                "allowable": f"≤ {allowable} мм",
                "result": result,
                "note": f"РД 03-606-03, кат. {weld_category}",
            }

        return {
            "defect_type": defect_type,
            "measured": f"{size_mm} мм",
            "allowable": "Требует экспертной оценки",
            "result": "requires_review",
            "note": "Требуется дополнительная экспертиза",
        }


_instance = RD03606Data()
get_card_fields = _instance.get_card_fields
generate_card_data = _instance.generate_card_data
get_quality_criteria = _instance.get_quality_criteria
evaluate_defect = _instance.evaluate_defect
