"""Мост между ИИ-консультантом и генератором техкарт.

Позволяет помощнику выступать посредником: собирает данные от
пользователя через чат и либо вызывает расчётное ядро генератора
напрямую (режим А — без списания лимита), либо запускает полную
генерацию техкарты (режим Б — списывается лимит подписки).
"""
import os
from datetime import datetime


# Коды схем генератора -> понятные пользователю обозначения
SCHEME_DISPLAY = {
    '5a': '3а', '5b': '3б', '5zh': '3г',
    '5d': '3д', '5g': '4а', '5v': '3в',
    '4_6': '4.6', '5zh': '3г',
}

# Обратный маппинг: что вводит пользователь -> код генератора
USER_SCHEME_TO_CODE = {
    '3а': '5a', '3б': '5b', '3г': '5zh',
    '3д': '5d', '3в': '5v', '4а': '5g', '4в': '5g',
}


def display_scheme(code: str) -> str:
    """Возвращает понятное пользователю обозначение схемы."""
    return SCHEME_DISPLAY.get(code, code)


def build_generator_input(params: dict, mode: str = 'A') -> dict:
    """Преобразует параметры мастера в формат input_data генератора.

    :param params: собранные мастером поля
    :param mode: 'A' — расчёт в чате, 'B' — полная генерация
    """
    mat_map = {
        'сталь': 'steel', 'алюминий': 'aluminum', 'титан': 'titanium',
        'al': 'aluminum', 'ti': 'titanium',
    }
    material = mat_map.get(params.get('material', 'сталь').lower(), 'steel')

    cat_map = {'I': 'I', 'II': 'II', 'III': 'III', '1': 'I', '2': 'II', '3': 'III'}
    category = cat_map.get(params.get('category', 'II').upper().strip(), 'II')

    scheme_user = params.get('scheme', '').strip().lower()
    scheme_code = USER_SCHEME_TO_CODE.get(scheme_user, '5a')

    try:
        outer_d = float(params.get('outer_diameter', params.get('D', '0')).replace(',', '.'))
    except (ValueError, AttributeError):
        outer_d = 0.0
    try:
        inner_d = float(params.get('inner_diameter', params.get('d', '0')).replace(',', '.'))
    except (ValueError, AttributeError):
        inner_d = 0.0
    try:
        thickness = float(params.get('thickness', '0').replace(',', '.'))
    except (ValueError, AttributeError):
        thickness = 0.0

    if outer_d > 0 and inner_d == 0:
        inner_d = outer_d - 2 * thickness
    wall = thickness

    try:
        focal = float(params.get('focal_spot', '0').replace(',', '.')) or 2.0
    except (ValueError, AttributeError):
        focal = 2.0
    try:
        K = float(params.get('sensitivity', '0').replace(',', '.')) or 0.2
    except (ValueError, AttributeError):
        K = 0.2

    input_data = {
        'object_name': params.get('object_name', 'Объект РГК'),
        'weld_number': params.get('weld_number', 'Шов-1'),
        'card_number': params.get('card_number', datetime.now().strftime('TC-%Y%m%d')),
        'object_type': 'pipe' if outer_d > 0 else 'flat',
        'material': material,
        'wall_thickness': wall,
        'outer_diameter': outer_d,
        'flat_length_mm': 0.0 if outer_d > 0 else (params.get('flat_length_mm') or 300.0),
        'weld_category': category,
        'source_code': params.get('source_code', ''),
        'focal_spot_mm': focal,
        'sfd_mm': float(params.get('sfd', '0') or 0),
        'required_sensitivity_mm': K,
        'control_volume_pct': 100,
        'welding_process': '30',
        'joint_designation': params.get('joint_designation', 'C1'),
        'joint_mobility': 'non_rotating',
        'iqi_side': params.get('iqi_side', 'source'),
        'film_name': params.get('film_name', ''),
        'scheme_type': scheme_code,
        'exposure_scheme_code': scheme_code,
    }
    return input_data


def run_calculation(params: dict) -> dict:
    """Режим А: вызывает расчётное ядро генератора, без списания лимита."""
    from techcards.generator import RadiographicTechCardCalculator
    input_data = build_generator_input(params, mode='A')
    calc = RadiographicTechCardCalculator(input_data)
    result = calc.calculate()
    return {
        'params': result,
        'errors': calc.errors,
        'warnings': calc.warnings,
        'mode': 'A',
        '_user_scheme': params.get('scheme', ''),
    }


def run_full_generation(params: dict, media_root: str, doc_code: str = 'rgk') -> dict:
    """Режим Б: полная генерация техкарты (DOCX + PDF) через генератор.

    ВНИМАНИЕ: вызывающий обязан предварительно проверить баланс
    (balance.can_create_techcard) и после успеха вызвать balance.use_credit.
    """
    from techcards.generator import generate_tech_card
    input_data = build_generator_input(params, mode='B')
    result = generate_tech_card(input_data, media_root)
    result['mode'] = 'B'
    return result


def format_calculation_summary(calc_result: dict) -> str:
    """Форматирует результат режима А в читаемый текст для чата."""
    p = calc_result.get('params', {})
    lines = []

    if calc_result.get('errors'):
        lines.append("⚠️ Ошибки расчёта:")
        lines.extend(f"  • {e}" for e in calc_result['errors'])
        lines.append("")

    lines.append("**Параметры РГК (расчёт генератора):**\n")

    # Источник
    src = p.get('source_code') or p.get('source_name', '')
    if src:
        lines.append(f"• Источник: {src}")

    # Чувствительность
    if p.get('sensitivity_K_mm') is not None:
        lines.append(f"• Чувствительность K: {p['sensitivity_K_mm']} мм")
    elif p.get('sensitivity_display'):
        lines.append(f"• Чувствительность: {p['sensitivity_display']}")

    # Геометрия
    scheme = p.get('exposure_scheme', {})
    if scheme:
        # Показываем схему, которую ввёл пользователь (понятно, без кодов 5v)
        user_scheme = calc_result.get('_user_scheme') or p.get('scheme_type', '')
        lines.append(f"• Схема: {user_scheme}")
        f_min = scheme.get('f_min_mm')
        if f_min is not None:
            lines.append(f"• f (фокусное расстояние) = {f_min:.1f} мм")
            if scheme.get('formula'):
                lines.append(f"  {scheme['formula']}")
            N = scheme.get('N')
            if N:
                lines.append(f"• Число экспозиций N: {N}")
            L = scheme.get('L_mm')
            if L:
                lines.append(f"• Длина участка L: {L:.1f} мм")

    # Плёнка
    film = p.get('film_class_info') or p.get('recommended_film_classes')
    if film:
        if isinstance(film, list) and film:
            lines.append(f"• Класс плёнки: {film[0].get('label', film[0].get('class', ''))}")
        elif isinstance(film, dict):
            lines.append(f"• Класс плёнки: {film.get('label', film.get('class', ''))}")

    # ИКИ
    iqi = p.get('iqi_info') or p.get('wire_iqi')
    if iqi:
        lines.append(f"• ИКИ: {iqi}")

    # ОШЗ
    if p.get('zone_width_mm'):
        lines.append(f"• ОШЗ (ширина снимка): {p['zone_width_mm']} мм")

    # Оптическая плотность
    if p.get('optical_density_min') is not None:
        lines.append(f"• Оптическая плотность: {p['optical_density_min']}–{p['optical_density_max']}")

    if calc_result.get('warnings'):
        lines.append("")
        lines.append("⚠️ Предупреждения:")
        lines.extend(f"  • {w}" for w in calc_result['warnings'])

    lines.append("\n_[Расчёт выполнен ядром генератора техкарт ГОСТ Р 50.05.07-2018]_")

    return '\n'.join(lines)