def _wizard_calculate(params: dict) -> str:
    """Финальный расчёт параметров РГК по собранным данным мастера."""
    from normative import gost_50_05_07 as M507
    from normative import gost_59023_2 as M59023
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

    category = params.get('category', 'I').upper().strip()
    scheme = params.get('scheme', '3г').strip().lower()
    try:
        focal_spot = float(params.get('focal_spot', '').replace(',', '.'))
    except (ValueError, AttributeError):
        focal_spot = 2.0
    try:
        sensitivity = float(params.get('sensitivity', '').replace(',', '.'))
    except (ValueError, AttributeError):
        sensitivity = 0.2

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
            lines.append(f"• Требуемая K: {row['sensitivity_K_mm']} мм")
    except Exception:
        pass

    # 3. Геометрия: f (по схеме)
    c = 2 * focal_spot / sensitivity if sensitivity > 0 else 4
    c_val = max(c, 4)
    scheme_lower = scheme.lower()

    scheme_formulas = {
        '3а': f"f = 0,7·c·(D−d)",
        '3б': f"f = 0,5·c·D",
        '3г': f"f = 0,5·[1,5·c·(D−d)−D]",
        '3д': f"f = 0,5·[c·(1,4·D−d)−D]",
        '4а': f"f = 0,7·c·(2·Rt+d)",
        '4в': f"f = 0,5·[1,5·c·(D*−d)−D*]",
    }
    formula = scheme_formulas.get(scheme_lower, '')
    if formula:
        lines.append(f"• Формула f: {formula}")
        lines.append(f"  где c = 2·Φ/K = 2·{focal_spot}/{sensitivity} = {c_val:.1f}")

    # 4. ОШЗ (ГОСТ Р 50.05.07-2018 п. 6.3.13)
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