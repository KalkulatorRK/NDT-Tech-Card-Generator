def _wizard_calculate(params: dict) -> str:
    """Финальный расчёт параметров РГК по собранным данным мастера.

    Переиспользует проверенную логику из normative.calculations
    (recommend_scheme + calc_exposure_parameters), чтобы исключить
    расхождения с генератором техкарт.
    """
    from normative import gost_50_05_07 as M507
    from normative import np_105_18 as M105
    from normative.calculations import (
        recommend_scheme, calc_exposure_parameters, SCHEME_INFO,
    )

    material = params.get('material', 'сталь').lower()
    if material in ('алюминий', 'aluminum', 'al'):
        mat_key = 'aluminum'
        mat_ru = 'алюминия'
    elif material in ('титан', 'titanium', 'ti'):
        mat_key = 'titanium'
        mat_ru = 'титана'
    else:
        mat_key = 'steel'
        mat_ru = 'стали'

    try:
        thickness = float(params.get('thickness', '').replace(',', '.'))
    except (ValueError, AttributeError):
        thickness = 0

    raw_cat = params.get('category', '').upper().strip()
    cat_map = {'I': 'I', 'II': 'II', 'III': 'III', '1': 'I', '2': 'II', '3': 'III'}
    category = cat_map.get(raw_cat, raw_cat)

    # Диаметры
    try:
        D = float(params.get('outer_diameter', params.get('D', '0')).replace(',', '.'))
    except (ValueError, AttributeError):
        D = 0.0
    try:
        d = float(params.get('inner_diameter', params.get('d', '0')).replace(',', '.'))
        if D > 0 and d == 0:
            d = D - 2 * thickness  # грубая оценка если только толщина
    except (ValueError, AttributeError):
        d = 0.0
    try:
        R = float(params.get('radius', '0').replace(',', '.'))
    except (ValueError, AttributeError):
        R = 0.0

    try:
        focal_spot = float(params.get('focal_spot', '').replace(',', '.'))
    except (ValueError, AttributeError):
        focal_spot = 2.0
    try:
        sensitivity = float(params.get('sensitivity', '').replace(',', '.'))
    except (ValueError, AttributeError):
        sensitivity = 0.2

    # Доступ внутрь (для 3г/3д/4а/4в)
    access_inside = params.get('access_inside', '').lower() in ('да', 'yes', 'есть', '1', 'true', '+')

    lines = [f"**Результат расчёта для {mat_ru}, {thickness:.0f} мм, кат. {category}**\n"]

    # 1. Источник излучения
    sources = M507.get_suitable_sources(thickness, mat_key)
    if sources:
        src_names = [s['name'] for s in sources]
        lines.append(f"• Источник: {', '.join(src_names)}")

    # 2. Чувствительность K
    try:
        row = M105.lookup_acceptance_criteria(mat_key, category, thickness)
        if row:
            lines.append(f"• Допустимая K: {row['sensitivity_K_mm']} мм")
    except Exception:
        pass

    # 3. Рекомендуемая схема + расчёт f
    if D > 0:
        # Маппинг выбора пользователя (3а/3г) на схемы генератора (5a/5zh)
        scheme_map = {
            '3а': '5a', '3б': '5b', '3г': '5zh',
            '3д': '5d', '4а': '5g', '4в': '5zh',
        }
        chosen = scheme_map.get(params.get('scheme', '').strip().lower())

        calc = calc_exposure_parameters(
            chosen, focal_spot, sensitivity,
            thickness_mm=thickness, d_outer_mm=D, d_inner_mm=d,
        )
        f_val = calc.get('f_min_mm')
        if f_val is not None:
            lines.append(f"• Рекомендуемая схема: {chosen} ({SCHEME_INFO.get(chosen, {}).get('name', '')})")
            lines.append(f"• f (фокусное расстояние) = {f_val:.1f} мм")
            if calc.get('formula'):
                lines.append(f"  {calc['formula']}")
            N = calc.get('N')
            if N:
                lines.append(f"• Число экспозиций N: {N}")
            L = calc.get('L_mm')
            if L:
                lines.append(f"• Длина участка L: {L:.1f} мм")
        else:
            lines.append(f"• Расчёт f не выполнен ({calc.get('error', 'нет данных')})")
    else:
        # Плоская деталь — схема 4_6
        calc = calc_exposure_parameters('4_6', focal_spot, sensitivity, thickness_mm=thickness)
        f_val = calc.get('f_min_mm')
        if f_val is not None:
            lines.append(f"• Схема: 4.6 (плоская деталь)")
            lines.append(f"• f (фокусное расстояние) = {f_val:.1f} мм")
            if calc.get('formula'):
                lines.append(f"  {calc['formula']}")

    # 4. ОШЗ
    zone = thickness if thickness <= 20 else 20
    lines.append(f"• ОШЗ: ≥5 мм в каждую сторону, мин. ширина снимка: {zone:.0f} мм")

    # 5. Оптическая плотность
    try:
        od = M507.OPTICAL_DENSITY.get(category, {})
        if od:
            lines.append(f"• Оптическая плотность D: {od['min']}–{od['max']}")
    except Exception:
        pass

    # 6. Перекрытие
    lines.append("• Перекрытие смежных участков: ≥20 мм")
    lines.append(f"\n_[ГОСТ Р 50.05.07-2018, приложение Г, табл. Г.1–Г.4, п. 6.3.13; НП-105-18, табл. 4.8]_")

    return '\n'.join(lines)