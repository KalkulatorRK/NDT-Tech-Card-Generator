"""
Данные ГОСТ Р 50.05.09-2018 «Система оценки соответствия в области
использования атомной энергии. Оценка соответствия в форме контроля.
Унифицированные методики. Капиллярный контроль».

Модуль содержит структурированные требования для ИИ-консультанта и
справочных вызовов (tools) по капиллярному контролю (КК / PT):
- классы чувствительности (табл. 1, прил. Б);
- условия окружающей среды;
- требования к ДМ (наборы), персоналу, техкартам;
- подготовка поверхности (шероховатость, обезжиривание);
- освещённость / УФ-облучённость (табл. 2, 3);
- минимальные времена контакта пенетранта и осмотра;
- рекомендуемые наборы ДМ (прил. А).

Источник: ГОСТ Р 50.05.09-2018 (введён в действие 01.03.2019).

ВАЖНО: при изменении стандарта актуализировать этот модуль по тексту НД.
"""

from __future__ import annotations

from typing import Optional

# ------------------------------------------------------------------
# Идентификатор документа
# ------------------------------------------------------------------
DOCUMENT_CODE = 'ГОСТ Р 50.05.09-2018'
DOCUMENT_SHORT = 'ГОСТ Р 50.05.09'
DOCUMENT_FULL_NAME = (
    'ГОСТ Р 50.05.09-2018 «Система оценки соответствия в области использования '
    'атомной энергии. Оценка соответствия в форме контроля. Унифицированные '
    'методики. Капиллярный контроль»'
)
DOCUMENT_EFFECTIVE_FROM = '2019-03-01'
METHOD_CODE = 'КК'
METHOD_NAME = 'капиллярный контроль'
METHOD_NAME_EN = 'Liquid penetrant testing (PT)'

# ------------------------------------------------------------------
# Условия окружающей среды (п. 5.5, 5.6)
# ------------------------------------------------------------------
AMBIENT_TEMP_MIN_C = -40
AMBIENT_TEMP_MAX_C = 40
AMBIENT_RH_MAX_PERCENT = 90
# п. 5.6 — выявление несплошностей с раскрытием ≥ 0,5 мм не гарантируется
DISCLOSURE_NOT_GUARANTEED_FROM_MM = 0.5

# Низкотемпературный режим подготовки / удаления пенетранта (п. 8.1.14, 8.2.2.4)
LOW_TEMP_MODE_MIN_C = -40
LOW_TEMP_MODE_MAX_C = 8

# ------------------------------------------------------------------
# Классы чувствительности — табл. 1 (п. 5.7, 5.8)
# Ширина раскрытия несплошности на контрольном образце, мкм
# ------------------------------------------------------------------
SENSITIVITY_CLASSES = {
    'I': {
        'code': 'I',
        'crack_width_um_min': None,
        'crack_width_um_max': 1.0,
        'description': 'Менее 1,0 мкм',
        'table': '1',
    },
    'II': {
        'code': 'II',
        'crack_width_um_min': 1.0,
        'crack_width_um_max': 10.0,
        'description': 'От 1,0 до 10,0 мкм включительно',
        'table': '1',
    },
    'III': {
        'code': 'III',
        'crack_width_um_min': 10.0,
        'crack_width_um_max': 100.0,
        'description': 'От 10,0 до 100,0 мкм включительно',
        'table': '1',
    },
}

# Приложение Б, табл. Б.1 — номинальная ширина раскрытия дефекта на КО, мкм
CONTROL_SAMPLE_CRACK_WIDTH_UM = {
    'I': {'nominal_um': 0.6, 'range_um': None},
    'II': {'nominal_um': None, 'range_um': (1.1, 8.5)},
    'III': {'nominal_um': None, 'range_um': (14.0, 96.0)},
}

# Длина тупиковой трещины для определения чувствительности (п. 5.7)
SENSITIVITY_CRACK_LENGTH_MIN_MM = 3.0

# ------------------------------------------------------------------
# Способы контроля
# ------------------------------------------------------------------
CONTROL_METHODS = {
    'color': {
        'code': 'цветной',
        'name': 'цветной способ',
        'definition': (
            'Метод капиллярного контроля, при котором обнаружение несплошностей '
            'производится путем регистрации цветного индикаторного следа в видимом '
            'излучении на фоне проявителя (п. 3.23).'
        ),
    },
    'fluorescent': {
        'code': 'люминесцентный',
        'name': 'люминесцентный способ',
        'definition': (
            'Метод капиллярного контроля с использованием люминесцентного пенетранта '
            'и регистрацией индикаторного следа в ультрафиолетовом излучении.'
        ),
    },
}

# ------------------------------------------------------------------
# Дефектоскопические материалы (п. 6.1.1)
# ------------------------------------------------------------------
DM_SET_COMPONENTS = (
    'индикаторный пенетрант',
    'очиститель ОК от пенетранта',
    'проявитель индикаторного следа дефекта',
)
# п. 6.1.1.3
DM_MIXING_SETS_FORBIDDEN = True

# Персонал (п. 6.2)
PERSONNEL_STANDARD = 'ГОСТ Р 50.05.11'

# ------------------------------------------------------------------
# Подготовка поверхности (п. 8.1.5–8.1.12)
# ------------------------------------------------------------------
# Основное требование: Ra 3,2 (Rz 20); допускается Ra 6,3 (Rz 40)
# при отсутствии недопустимого окрашенного фона (примечание к п. 8.1.5).
SURFACE_ROUGHNESS_RA_TARGET = 3.2
SURFACE_ROUGHNESS_RZ_TARGET = 20.0
SURFACE_ROUGHNESS_RA_MAX_ALLOWED = 6.3
SURFACE_ROUGHNESS_RZ_MAX_ALLOWED = 40.0
SURFACE_ROUGHNESS_STANDARD = 'ГОСТ 9378'

# Обезжиривание: ацетон, спирт или денатурат; керосин/сольвент — запрещены (п. 8.1.11)
DEGREASING_ALLOWED = ('ацетон', 'спирт', 'денатурат')
DEGREASING_FORBIDDEN = ('керосин', 'сольвент')
# Альтернатива внутри сосуда и т.п. (п. 8.1.12): 5–10% водный раствор моющего средства
DEGREASING_ALTERNATIVE = '5%-10%-ный водный раствор моющего средства'

# После МПД (п. 8.1.15): размагничивание по ГОСТ Р 50.05.06, промывка ацетоном,
# сушка 170–220 °C, 50–60 мин
AFTER_MT_DRY_TEMP_MIN_C = 170
AFTER_MT_DRY_TEMP_MAX_C = 220
AFTER_MT_DRY_TIME_MIN_MIN = 50
AFTER_MT_DRY_TIME_MAX_MIN = 60

# ------------------------------------------------------------------
# Освещённость — табл. 2 (п. 8.1.23), лк
# Ключи: fluorescent_* — люминесцентные лампы; incandescent_* — накаливания
# ------------------------------------------------------------------
ILLUMINANCE_LX = {
    'I': {
        'fluorescent_combined': 2500,
        'fluorescent_general': 750,
        'incandescent_combined': 2000,
        'incandescent_general': 500,
    },
    'II': {
        'fluorescent_combined': 2500,
        'fluorescent_general': 750,
        'incandescent_combined': 2000,
        'incandescent_general': 500,
    },
    'III': {
        'fluorescent_combined': 2000,
        'fluorescent_general': 500,
        'incandescent_combined': 1500,
        'incandescent_general': 400,
    },
}

# УФ-облучённость — табл. 3 (п. 8.1.24), мкВт/см² (в тексте НД — мкВт/см)
UV_IRRADIANCE_UW_PER_CM2 = {
    'I': 3000,
    'II': 3000,
}

# ------------------------------------------------------------------
# Времена операций (п. 8.2.1.1, 8.2.1.3, 8.3)
# ------------------------------------------------------------------
# Минимальное время контакта пенетранта с поверхностью
PENETRANT_CONTACT_MIN_WELD_MIN = 5   # сварные соединения, включая околошовную зону
PENETRANT_CONTACT_MIN_BASE_METAL_MIN = 10  # основной металл
# После контакта со щелочной/кислой средой — рекомендуется до 20 мин (п. 8.2.1.3)
PENETRANT_CONTACT_RECOMMENDED_AFTER_CHEM_MIN = 20

# Осмотр при отсутствии указаний производителя (п. 8.3.2)
DEVELOPER_INSPECTION_FIRST_MIN = (3, 5)   # через 3–5 мин после нанесения
DEVELOPER_INSPECTION_SECOND_MIN = 20      # через 20 мин после высыхания
# Если ориентировочное время проявления производителя ≥ 20 мин — уточняют на КО (п. 8.3.1)
DEVELOPER_TIME_VERIFY_ON_KO_FROM_MIN = 20

# Режим накопления красителя (п. 8.2.1.9): проявитель ≥ 20 мин и др.
DYE_ACCUMULATION_DEVELOPER_MIN_MIN = 20

# Контрольные образцы (прил. Б): Rz*20 мкм (см. 8.1.5)
KO_SURFACE_RZ_UM = 20.0

# ------------------------------------------------------------------
# Рекомендуемые наборы ДМ — прил. А, табл. А.1 (справочное)
# upper_threshold_um — верхний порог чувствительности набора, мкм
# ------------------------------------------------------------------
RECOMMENDED_DM_KITS = [
    {
        'name': 'MET-L-CHEK FP97A(M)/E58D/D70',
        'method': 'люминесцентный',
        'temp_c': (10, 50),
        'class': 'I',
        'upper_threshold_um': 1.0,
        'threshold_note': 'Менее 1,0',
    },
    {
        'name': 'ARDROX 970P23/9PR88/9D1B',
        'method': 'люминесцентный',
        'temp_c': (10, 50),
        'class': 'I',
        'upper_threshold_um': 1.0,
        'threshold_note': 'Менее 1,0',
    },
    {
        'name': 'ЛЮМ-33ОВ (ЛЖ-18НВ/ОЖ-7А/ПР-15А)',
        'method': 'люминесцентный',
        'temp_c': (18, 30),
        'class': 'I',
        'upper_threshold_um': 1.0,
        'threshold_note': 'Менее 1,0',
    },
    {
        'name': 'ЛЮМ1-ОВ (ЛЖ-6А/ОЖ-1М/ПР-1)',
        'method': 'люминесцентный',
        'temp_c': (18, 28),
        'class': 'I',
        'upper_threshold_um': 1.0,
        'threshold_note': 'Менее 1,0',
    },
    {
        'name': 'I-И НМ П (или П)',
        'method': 'цветной',
        'temp_c': (8, 40),
        'class': 'I',
        'upper_threshold_um': 1.0,
        'threshold_note': 'Менее 1,0',
    },
    {
        'name': 'II-И М П',
        'method': 'цветной',
        'temp_c': (8, 40),
        'class': 'II',
        'upper_threshold_um': 1.0,
        'threshold_note': 'От 1,0',
    },
    {
        'name': 'II-И М П (или П)',
        'method': 'цветной',
        'temp_c': (8, 40),
        'class': 'II',
        'upper_threshold_um': 1.0,
        'threshold_note': 'От 1,0',
    },
    {
        'name': 'II-И М (или М) П (или П)',
        'method': 'цветной',
        'temp_c': (-40, 40),
        'class': 'II',
        'upper_threshold_um': 1.0,
        'threshold_note': 'От 1,0',
    },
    {
        'name': 'II-СиМ (аэрозольный)',
        'method': 'цветной',
        'temp_c': (-40, 40),
        'class': 'II',
        'upper_threshold_um': 1.0,
        'threshold_note': 'От 1,0',
    },
    {
        'name': 'ЦМ-15В КиМ (аэрозольный)',
        'method': 'цветной',
        'temp_c': (18, 28),
        'class': 'II',
        'upper_threshold_um': 1.0,
        'threshold_note': 'От 1,0',
    },
    {
        'name': 'ЛЮМ-34В (ЛЖ-20В/ОЖ-7А/ПР-15А)',
        'method': 'люминесцентный',
        'temp_c': (18, 30),
        'class': 'II',
        'upper_threshold_um': 1.0,
        'threshold_note': 'От 1,0',
    },
    {
        'name': 'ЛЮМ-35С (ЛЖ-27С/ОЖ-7А/ПР-15А)',
        'method': 'люминесцентный',
        'temp_c': (18, 30),
        'class': 'II',
        'upper_threshold_um': 1.5,
        'threshold_note': 'От 1,5',
    },
    {
        'name': 'NORD-TEST U88/U87/U89',
        'method': 'цветной',
        'temp_c': (10, 50),
        'class': 'II',
        'upper_threshold_um': 1.0,
        'threshold_note': 'От 1,0',
    },
    {
        'name': 'SPOTCHECK SKL-SP1/SKC-S/SKD-S2',
        'method': 'цветной',
        'temp_c': (10, 40),
        'class': 'II',
        'upper_threshold_um': 2.0,
        'threshold_note': 'От 2,0',
    },
    {
        'name': 'MET-L-CHEK VP30/NPU/D70',
        'method': 'цветной',
        'temp_c': (10, 50),
        'class': 'II',
        'upper_threshold_um': 3.0,
        'threshold_note': 'От 3,0',
    },
    {
        'name': 'SHERWIN DP-55/DR-60/D-100',
        'method': 'цветной',
        'temp_c': (10, 50),
        'class': 'II',
        'upper_threshold_um': 3.0,
        'threshold_note': 'От 3,0',
    },
    {
        'name': 'SPOTCHECK SK1-WP/вода/SKD-S2',
        'method': 'цветной',
        'temp_c': (10, 40),
        'class': 'II',
        'upper_threshold_um': 4.0,
        'threshold_note': 'От 4,0',
    },
    {
        'name': 'R-Тест ОН-51/ПН-52/ПН-53',
        'method': 'цветной',
        'temp_c': (-30, 40),
        'class': 'II',
        'upper_threshold_um': 1.0,
        'threshold_note': 'От 1,0',
    },
    {
        'name': 'R-Тест ОС-41/ПС-42/ПС-43',
        'method': 'цветной',
        'temp_c': (-5, 45),
        'class': 'II',
        'upper_threshold_um': 2.0,
        'threshold_note': 'От 2,0',
    },
]

# Содержание технологической карты (п. 7.3) — краткие ключи
TECH_CARD_REQUIRED_ITEMS = (
    'организация — владелец ОК',
    'наименование ОК, участок, идентификаторы',
    'ссылки на инструкции / НД / ТУ / КД',
    'объём контроля (зоны при выборочном)',
    'координаты и размеры участков, нумерация',
    'способ контроля',
    'класс чувствительности',
    'набор ДМ',
    'условия контроля (температура, влажность, освещённость)',
    'набор КО с регистрационными номерами',
    'приборы, аппаратура, освещение, вспомогательные материалы',
    'технология подготовки поверхности',
    'шероховатость контролируемой поверхности',
    'последовательность операций контроля',
    'нормы оценки качества ОК',
)


# ------------------------------------------------------------------
# Функции справочника
# ------------------------------------------------------------------

def get_sensitivity_class_by_crack_um(width_um: float) -> Optional[str]:
    """
    Класс чувствительности по ширине раскрытия на КО (табл. 1).

    :param width_um: ширина раскрытия, мкм
    :return: 'I' | 'II' | 'III' | None
    """
    if width_um is None or width_um < 0:
        return None
    if width_um < 1.0:
        return 'I'
    if width_um <= 10.0:
        return 'II'
    if width_um <= 100.0:
        return 'III'
    return None


def get_sensitivity_class_info(class_code: str) -> Optional[dict]:
    """Возвращает описание класса чувствительности по коду I/II/III."""
    if not class_code:
        return None
    key = class_code.strip().upper().replace('1', 'I').replace('2', 'II').replace('3', 'III')
    # нормализация латинских цифр уже; поддержка «класс 2»
    aliases = {'1': 'I', '2': 'II', '3': 'III'}
    key = aliases.get(class_code.strip(), key)
    return SENSITIVITY_CLASSES.get(key)


def get_illuminance(class_code: str) -> Optional[dict]:
    """Освещённость по табл. 2 для класса чувствительности."""
    info = get_sensitivity_class_info(class_code)
    if not info:
        return None
    return ILLUMINANCE_LX.get(info['code'])


def get_uv_irradiance(class_code: str) -> Optional[int]:
    """УФ-облучённость по табл. 3 (мкВт/см²) для I и II классов."""
    info = get_sensitivity_class_info(class_code)
    if not info:
        return None
    return UV_IRRADIANCE_UW_PER_CM2.get(info['code'])


def get_min_penetrant_contact_min(object_kind: str = 'weld') -> int:
    """
    Минимальное время контакта пенетранта, мин (п. 8.2.1.1).

    :param object_kind: 'weld' | 'base_metal' | 'chem' (после щелочи/кислоты)
    """
    kind = (object_kind or 'weld').strip().lower()
    if kind in ('base', 'base_metal', 'металл', 'основной', 'ом'):
        return PENETRANT_CONTACT_MIN_BASE_METAL_MIN
    if kind in ('chem', 'acid', 'alkali', 'щелоч', 'кислот'):
        return PENETRANT_CONTACT_RECOMMENDED_AFTER_CHEM_MIN
    return PENETRANT_CONTACT_MIN_WELD_MIN


def is_ambient_ok(temp_c: float, rh_percent: Optional[float] = None) -> bool:
    """Проверка условий п. 5.5 (температура и опционально влажность)."""
    if temp_c < AMBIENT_TEMP_MIN_C or temp_c > AMBIENT_TEMP_MAX_C:
        return False
    if rh_percent is not None and rh_percent > AMBIENT_RH_MAX_PERCENT:
        return False
    return True


def format_sensitivity_table() -> str:
    """Текст табл. 1 для RAG/tools."""
    lines = [
        f'{DOCUMENT_CODE}, таблица 1 — классы чувствительности капиллярного контроля:',
    ]
    for code, row in SENSITIVITY_CLASSES.items():
        lines.append(f'  класс {code}: {row["description"]} (ширина раскрытия на КО).')
    lines.append(
        f'Чувствительность определяют по среднему раскрытию неразветвлённой тупиковой '
        f'трещины длиной не менее {SENSITIVITY_CRACK_LENGTH_MIN_MM:g} мм (п. 5.7). '
        f'Класс устанавливают по проектной (конструкторской) документации (п. 5.8).'
    )
    return ' '.join(lines)


def format_ambient_rules() -> str:
    """Текст условий среды и ограничения по раскрытию."""
    return (
        f'{DOCUMENT_CODE}, п. 5.5: капиллярный контроль проводят при температуре '
        f'окружающего воздуха от минус {abs(AMBIENT_TEMP_MIN_C)} °C до плюс '
        f'{AMBIENT_TEMP_MAX_C} °C и относительной влажности воздуха не более '
        f'{AMBIENT_RH_MAX_PERCENT}%. '
        f'{DOCUMENT_CODE}, п. 5.6: выявление несплошностей с шириной раскрытия '
        f'{DISCLOSURE_NOT_GUARANTEED_FROM_MM} мм и более капиллярным контролем '
        f'не гарантируется.'
    )


def format_dm_rules() -> str:
    """Требования к наборам ДМ."""
    comps = ', '.join(DM_SET_COMPONENTS)
    return (
        f'{DOCUMENT_CODE}, п. 6.1.1.1: ДМ применяют в виде наборов, в которые входят: '
        f'{comps}. '
        f'Рекомендуемые совместимые наборы — приложение А. '
        f'п. 6.1.1.3: не допускается использование ДМ из различных наборов.'
    )


def kits_for_class(class_code: str) -> list:
    """Наборы из прил. А для заданного класса чувствительности."""
    info = get_sensitivity_class_info(class_code)
    if not info:
        return []
    return [k for k in RECOMMENDED_DM_KITS if k['class'] == info['code']]
