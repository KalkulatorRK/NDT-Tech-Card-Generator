def _wizard_calculate(params: dict) -> str:
    """Финальный расчёт параметров РГК по собранным данным мастера."""
    from normative import gost_50_05_07 as M507
    from normative import np_105_18 as M105

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

    scheme = params.get('scheme', '').strip().lower()
    VALID_SCHEMES = ('3а', '3б', '3г', '3д', '4а', '4в')
    if scheme not in VALID_SCHEMES:
        return f"Схема «{scheme}» не поддерживается. Допустимые: {', '.join(VALID_SCHEMES)}."

    try:
        focal_spot = float(params.get('focal_spot', '').replace(',', '.'))
    except (ValueError, AttributeError):
        focal_spot = 2.0
    try:
        sensitivity = float(params.get('sensitivity', '').replace(',', '.'))
    except (ValueError, AttributeError):
        sensitivity = 0.2

    # Диаметры для схем 3а-3д: D (нар.), d (внутр.)
    D = None
    d = None
    R = None
    t = None
    if scheme in ('3а', '3б', '3г', '3д'):
        try:
            D = float(params.get('outer_diameter', '').replace(',', '.'))
        except (ValueError, AttributeError):
            pass
        try:
            d = float(params.get('inner_diameter', '').replace(',', '.'))
        except (ValueError, AttributeError):
            pass
    elif scheme in ('4а', '4в'):
        try:
            R = float(params.get('radius', '').replace(',', '.'))
        except (ValueError, AttributeError):
            pass
        try:
            t = float(params.get('wall_thickness', '').replace(',', '.'))
        except (ValueError, AttributeError):
            pass
        try:
            d = float(params.get('inner_diameter', '').replace(',', '.'))
        except (ValueError, AttributeError):
            pass

    lines = [f"**Результат расчёта для {mat_ru}, {thickness:.0f} мм, кат. {category}, схема {scheme}**\n"]

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

    # 3. Геометрия: f
    if sensitivity > 0:
        c = max(2 * focal_spot / sensitivity, 4)
    else:
        c = 4

    if scheme in ('3а', '3б', '3г', '3д') and D is not None and d is not None:
        if scheme == '3а':
            f = 0.7 * c * (D - d)
        elif scheme == '3б':
            f = 0.5 * c * D
        elif scheme == '3г':
            f = 0.5 * (1.5 * c * (D - d) - D)
        elif scheme == '3д':
            f = 0.5 * (c * (1.4 * D - d) - D)
        else:
            f = None
        if f and f > 0:
            lines.append(f"• f (фокусное расстояние) = {f:.1f} мм")
            lines.append(f"• L (длина участка) ≤ {0.8 * f:.1f} мм (по Г.2)")
            lines.append(f"  где c = 2·Φ/K = 2·{focal_spot}/{sensitivity} = {c:.1f}")
            lines.append(f"  D = {D:.0f} мм, d = {d:.0f} мм")
    elif scheme in ('4а', '4в') and R is not None and t is not None and d is not None:
        if scheme == '4а':
            f = 0.7 * c * (2 * R + t + d)
        else:
            D_star = d + 2 * R + t
            f = 0.5 * (1.5 * c * (D_star - d) - D_star)
        if f and f > 0:
            lines.append(f"• f (фокусное расстояние) = {f:.1f} мм")
            lines.append(f"  где c = 2·Φ/K = 2·{focal_spot}/{sensitivity} = {c:.1f}")

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