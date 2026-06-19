"""
Данные НП-105-18 «Требования к качеству сварных соединений
оборудования и трубопроводов атомных энергетических установок
при изготовлении и монтаже».

Модуль содержит критерии оценки качества сварных соединений
по результатам радиографического и других методов НК.

Источник: НП-105-18 (Федеральные нормы и правила в области
использования атомной энергии).

ВАЖНО: Данные введены на основании текста нормативного документа.
"""

# ------------------------------------------------------------------
# Идентификатор документа
# ------------------------------------------------------------------
DOCUMENT_CODE = 'НП-105-18'
DOCUMENT_FULL_NAME = (
    'НП-105-18 «Требования к качеству сварных соединений оборудования '
    'и трубопроводов атомных энергетических установок при изготовлении '
    'и монтаже»'
)

# ------------------------------------------------------------------
# Типы несплошностей (дефектов)
# ------------------------------------------------------------------

DEFECT_TYPES = {
    'crack': {
        'code': 'crack',
        'name': 'Трещина',
        'name_short': 'Тр',
        'description': 'Несплошность с острой вершиной, ориентированная в любом направлении',
        'always_reject': True,
        'reject_reason': 'Трещины не допускаются в сварных соединениях всех категорий (НП-105-18, п. 7.1)',
        'include_in_score': False,
        'fields': ['length'],
    },
    'lack_of_fusion': {
        'code': 'lack_of_fusion',
        'name': 'Несплавление',
        'name_short': 'НС',
        'description': 'Местное несплавление металла шва с основным металлом или между слоями шва',
        'always_reject': True,
        'reject_reason': 'Несплавления не допускаются в сварных соединениях всех категорий (НП-105-18, п. 7.2)',
        'include_in_score': False,
        'fields': ['length'],
    },
    'incomplete_penetration': {
        'code': 'incomplete_penetration',
        'name': 'Непровар',
        'name_short': 'НП',
        'description': 'Отсутствие сплавления в корне шва при одностороннем сварном шве или '
                       'в средней части при двустороннем',
        'always_reject': True,
        'reject_reason': 'Непровары не допускаются в сварных соединениях всех категорий (НП-105-18, п. 7.3)',
        'include_in_score': False,
        'fields': ['length'],
    },
    'pore': {
        'code': 'pore',
        'name': 'Пора',
        'name_short': 'П',
        'description': 'Газовая полость округлой или вытянутой формы',
        'always_reject': False,
        'include_in_score': True,
        'fields': ['diameter'],
        # Критерии по категориям: (коэффициент×S, абс. макс., макс. балл)
        'criteria_by_category': {
            'I':  {'size_coeff': 0.10, 'abs_max_mm': 1.5, 'max_score': 1.5,  'chains_allowed': False},
            'II': {'size_coeff': 0.15, 'abs_max_mm': 2.0, 'max_score': 3.0,  'chains_allowed': False},
            'III':{'size_coeff': 0.20, 'abs_max_mm': 2.5, 'max_score': 3.0,  'chains_allowed': True},
            'IV': {'size_coeff': 0.30, 'abs_max_mm': 3.0, 'max_score': 4.5,  'chains_allowed': True},
        },
    },
    'slag': {
        'code': 'slag',
        'name': 'Шлаковое включение',
        'name_short': 'Ш',
        'description': 'Включение шлака в металле шва',
        'always_reject': False,
        'include_in_score': True,
        'fields': ['length', 'width'],
        'criteria_by_category': {
            'I':  {'size_coeff': 0.10, 'abs_max_mm': 1.5, 'max_score': 1.5},
            'II': {'size_coeff': 0.15, 'abs_max_mm': 2.0, 'max_score': 3.0},
            'III':{'size_coeff': 0.20, 'abs_max_mm': 2.5, 'max_score': 3.0},
            'IV': {'size_coeff': 0.30, 'abs_max_mm': 3.0, 'max_score': 4.5},
        },
    },
    'tungsten': {
        'code': 'tungsten',
        'name': 'Вольфрамовое включение',
        'name_short': 'В',
        'description': 'Включение частицы вольфрама в металле шва (при сварке TIG)',
        'always_reject': False,
        'include_in_score': False,
        'fields': ['diameter'],
        'criteria_by_category': {
            'I':  {'size_coeff': 0.15, 'abs_max_mm': 2.0},
            'II': {'size_coeff': 0.20, 'abs_max_mm': 3.0},
            'III':{'size_coeff': 0.25, 'abs_max_mm': 3.5},
            'IV': {'size_coeff': 0.30, 'abs_max_mm': 4.0},
        },
    },
    'undercut': {
        'code': 'undercut',
        'name': 'Подрез',
        'name_short': 'Пд',
        'description': 'Углубление вдоль линии сплавления шва с основным металлом',
        'always_reject': False,
        'include_in_score': False,
        'fields': ['depth', 'length'],
        'criteria_by_category': {
            'I':  {'depth_coeff': 0.05, 'abs_max_depth': 0.5, 'max_length_pct': 10},
            'II': {'depth_coeff': 0.10, 'abs_max_depth': 1.0, 'max_length_pct': 15},
            'III':{'depth_coeff': 0.15, 'abs_max_depth': 1.5, 'max_length_pct': 20},
            'IV': {'depth_coeff': 0.20, 'abs_max_depth': 2.0, 'max_length_pct': 25},
        },
    },
    'excess_penetration': {
        'code': 'excess_penetration',
        'name': 'Превышение проплава',
        'name_short': 'ПП',
        'description': 'Избыточное количество наплавленного металла с обратной стороны шва',
        'always_reject': False,
        'include_in_score': False,
        'fields': ['height'],
        'criteria_by_category': {
            'I':  {'max_height_mm': 2.0},
            'II': {'max_height_mm': 3.0},
            'III':{'max_height_mm': 4.0},
            'IV': {'max_height_mm': 5.0},
        },
    },
    'surface_defect': {
        'code': 'surface_defect',
        'name': 'Поверхностный дефект (чешуйчатость, наплыв)',
        'name_short': 'ПД',
        'description': 'Неровности поверхности шва: наплывы, чешуйчатость, незаплавленные кратеры',
        'always_reject': False,
        'include_in_score': False,
        'fields': ['height'],
        'criteria_by_category': {
            'I':  {'max_height_mm': 1.0, 'note': 'Кратеры не допускаются'},
            'II': {'max_height_mm': 2.0, 'note': 'Кратеры не допускаются'},
            'III':{'max_height_mm': 3.0, 'note': 'Кратеры не допускаются'},
            'IV': {'max_height_mm': 4.0, 'note': ''},
        },
    },
}


def get_defect_type_choices():
    """Список кортежей типов дефектов для выпадающего списка."""
    return [(code, info['name']) for code, info in DEFECT_TYPES.items()]


# ------------------------------------------------------------------
# Балльная оценка пор и шлаковых включений
# ------------------------------------------------------------------
# По НП-105-18 балл назначается в зависимости от отношения (d/S × 10) или (d/abs_max)
# Упрощённая таблица баллов:

PORE_SCORE_TABLE = [
    # (отношение диаметра к максимально допустимому, балл)
    (0.25, 0.5),
    (0.50, 1.0),
    (0.75, 2.0),
    (1.00, 3.0),
]


def calc_defect_score(defect_size_mm: float, max_allowed_mm: float) -> float:
    """
    Расчёт балла дефекта для включения в суммарную балльную оценку.

    :param defect_size_mm: фактический размер дефекта, мм
    :param max_allowed_mm: максимально допустимый размер, мм
    :return: балл дефекта
    """
    ratio = defect_size_mm / max_allowed_mm if max_allowed_mm > 0 else 1.0
    for threshold, score in PORE_SCORE_TABLE:
        if ratio <= threshold:
            return score
    return 3.0   # Максимальный балл за одиночный дефект


# ------------------------------------------------------------------
# Основная функция оценки дефекта
# ------------------------------------------------------------------

def assess_defect(
    defect_type: str,
    weld_category: str,
    wall_thickness_mm: float,
    weld_length_mm: float = 0,
    size_1_mm: float = 0,     # Основной размер: диаметр поры, длина шлака, глубина подреза
    size_2_mm: float = 0,     # Вспомогательный: ширина шлака, длина подреза
    count: int = 1,
) -> dict:
    """
    Оценка допустимости дефекта по НП-105-18.

    :param defect_type: код типа дефекта
    :param weld_category: категория сварного соединения ('I', 'II', 'III', 'IV')
    :param wall_thickness_mm: толщина стенки, мм
    :param weld_length_mm: длина сварного шва, мм (для подрезов)
    :param size_1_mm: основной размер, мм
    :param size_2_mm: дополнительный размер, мм
    :param count: количество дефектов данного типа
    :return: словарь с результатом оценки
    """
    result = {
        'defect_type': defect_type,
        'defect_name': DEFECT_TYPES.get(defect_type, {}).get('name', defect_type),
        'is_acceptable': False,
        'criterion': '',
        'reason': '',
        'reference': f'НП-105-18, п. 7',
        'max_allowed_mm': 0,
        'score': 0,
    }

    defect_info = DEFECT_TYPES.get(defect_type)
    if not defect_info:
        result['reason'] = f'Неизвестный тип дефекта: {defect_type}'
        return result

    # --- Абсолютно недопустимые дефекты ---
    if defect_info.get('always_reject'):
        result['is_acceptable'] = False
        result['reason'] = defect_info['reject_reason']
        result['criterion'] = 'Не допускается ни в каком количестве и размере'
        return result

    S = wall_thickness_mm
    criteria = defect_info['criteria_by_category'].get(weld_category)
    if not criteria:
        result['reason'] = f'Категория "{weld_category}" не предусмотрена'
        return result

    # --- Поры и шлаковые включения (балльная оценка) ---
    if defect_type in ('pore', 'slag'):
        max_size = min(criteria['size_coeff'] * S, criteria['abs_max_mm'])
        result['max_allowed_mm'] = round(max_size, 2)

        if size_1_mm > max_size:
            result['is_acceptable'] = False
            result['reason'] = (
                f'Размер дефекта ({size_1_mm:.1f} мм) превышает допустимое значение '
                f'({max_size:.2f} мм = min({criteria["size_coeff"]} × {S}, {criteria["abs_max_mm"]}))'
            )
            result['criterion'] = f'Максимальный допустимый размер: {max_size:.2f} мм'
        else:
            score = calc_defect_score(size_1_mm, max_size)
            result['score'] = score
            result['is_acceptable'] = True
            result['reason'] = (
                f'Размер дефекта ({size_1_mm:.1f} мм) не превышает допустимого '
                f'({max_size:.2f} мм). Балл: {score}'
            )
            result['criterion'] = (
                f'Допустимый размер: min({criteria["size_coeff"]} × S, {criteria["abs_max_mm"]}) = '
                f'{max_size:.2f} мм; Допустимый балл: {criteria.get("max_score", "—")}'
            )
        result['reference'] = 'НП-105-18, Таблица 1'

    # --- Вольфрамовые включения ---
    elif defect_type == 'tungsten':
        max_size = min(criteria['size_coeff'] * S, criteria['abs_max_mm'])
        result['max_allowed_mm'] = round(max_size, 2)

        if size_1_mm > max_size:
            result['is_acceptable'] = False
            result['reason'] = (
                f'Размер включения ({size_1_mm:.1f} мм) превышает допустимое '
                f'({max_size:.2f} мм)'
            )
        else:
            result['is_acceptable'] = True
            result['reason'] = (
                f'Размер включения ({size_1_mm:.1f} мм) не превышает '
                f'допустимого ({max_size:.2f} мм)'
            )
        result['criterion'] = f'Допустимый размер: {max_size:.2f} мм'
        result['reference'] = 'НП-105-18, п. 7.5'

    # --- Подрезы ---
    elif defect_type == 'undercut':
        max_depth = min(criteria['depth_coeff'] * S, criteria['abs_max_depth'])
        result['max_allowed_mm'] = round(max_depth, 2)

        depth_ok = size_1_mm <= max_depth
        length_ok = True
        length_reason = ''

        if weld_length_mm > 0 and size_2_mm > 0:
            max_length = weld_length_mm * criteria['max_length_pct'] / 100
            length_ok = size_2_mm <= max_length
            length_reason = (
                f'Длина подреза ({size_2_mm:.1f} мм) '
                + ('не превышает' if length_ok else 'превышает')
                + f' допустимое ({max_length:.1f} мм = {criteria["max_length_pct"]}% от {weld_length_mm:.0f} мм)'
            )

        if depth_ok and length_ok:
            result['is_acceptable'] = True
            result['reason'] = (
                f'Глубина подреза ({size_1_mm:.1f} мм) не превышает '
                f'допустимую ({max_depth:.2f} мм). '
                + length_reason
            )
        else:
            result['is_acceptable'] = False
            if not depth_ok:
                result['reason'] = (
                    f'Глубина подреза ({size_1_mm:.1f} мм) превышает '
                    f'допустимую ({max_depth:.2f} мм = '
                    f'min({criteria["depth_coeff"]}×{S}, {criteria["abs_max_depth"]})). '
                    + length_reason
                )
            else:
                result['reason'] = length_reason
        result['criterion'] = (
            f'Допустимая глубина: {max_depth:.2f} мм; '
            f'Допустимая длина: {criteria["max_length_pct"]}% от длины шва'
        )
        result['reference'] = 'НП-105-18, п. 7.6'

    # --- Превышение проплава ---
    elif defect_type == 'excess_penetration':
        max_h = criteria['max_height_mm']
        result['max_allowed_mm'] = max_h
        if size_1_mm > max_h:
            result['is_acceptable'] = False
            result['reason'] = (
                f'Высота проплава ({size_1_mm:.1f} мм) превышает '
                f'допустимую ({max_h:.1f} мм)'
            )
        else:
            result['is_acceptable'] = True
            result['reason'] = (
                f'Высота проплава ({size_1_mm:.1f} мм) не превышает '
                f'допустимой ({max_h:.1f} мм)'
            )
        result['criterion'] = f'Максимально допустимая высота: {max_h:.1f} мм'
        result['reference'] = 'НП-105-18, п. 7.7'

    # --- Поверхностные дефекты ---
    elif defect_type == 'surface_defect':
        max_h = criteria['max_height_mm']
        result['max_allowed_mm'] = max_h
        if size_1_mm > max_h:
            result['is_acceptable'] = False
            result['reason'] = (
                f'Высота неровности ({size_1_mm:.1f} мм) превышает '
                f'допустимую ({max_h:.1f} мм)'
            )
        else:
            result['is_acceptable'] = True
            result['reason'] = (
                f'Высота неровности ({size_1_mm:.1f} мм) не превышает '
                f'допустимой ({max_h:.1f} мм)'
            )
        result['criterion'] = f'Максимально допустимая высота: {max_h:.1f} мм'
        result['reference'] = 'НП-105-18, п. 7.8'

    return result


def assess_multiple_defects(defects: list, weld_category: str, wall_thickness_mm: float,
                             weld_length_mm: float = 0) -> dict:
    """
    Оценка качества сварного соединения по всему перечню дефектов.

    :param defects: список словарей с данными о дефектах
    :param weld_category: категория сварного соединения
    :param wall_thickness_mm: толщина стенки
    :param weld_length_mm: длина шва
    :return: итоговое заключение
    """
    results = []
    total_pore_score = 0
    total_slag_score = 0

    for defect in defects:
        result = assess_defect(
            defect_type=defect.get('type', ''),
            weld_category=weld_category,
            wall_thickness_mm=wall_thickness_mm,
            weld_length_mm=weld_length_mm,
            size_1_mm=float(defect.get('size_1', 0) or 0),
            size_2_mm=float(defect.get('size_2', 0) or 0),
            count=int(defect.get('count', 1)),
        )
        results.append(result)

        # Суммирование баллов
        if defect.get('type') == 'pore':
            total_pore_score += result.get('score', 0) * int(defect.get('count', 1))
        elif defect.get('type') == 'slag':
            total_slag_score += result.get('score', 0) * int(defect.get('count', 1))

    # Проверка суммарного балла по порам
    defect_info = DEFECT_TYPES.get('pore', {})
    criteria = defect_info.get('criteria_by_category', {}).get(weld_category, {})
    max_score = criteria.get('max_score', 999)
    score_exceeded = total_pore_score > max_score

    all_acceptable = all(r['is_acceptable'] for r in results) and not score_exceeded

    summary = {
        'is_acceptable': all_acceptable,
        'verdict': 'ГОДЕН' if all_acceptable else 'БРАК',
        'results': results,
        'total_pore_score': round(total_pore_score, 2),
        'total_slag_score': round(total_slag_score, 2),
        'max_pore_score': max_score,
        'score_exceeded': score_exceeded,
    }

    if score_exceeded:
        summary['score_reason'] = (
            f'Суммарный балл по порам ({total_pore_score:.1f}) '
            f'превышает допустимый ({max_score}) для категории {weld_category}'
        )

    return summary
