"""
Пользовательские названия и описания схем просвечивания.

Внутренние коды (5a, 5b, …) используются только в логике расчёта.
В интерфейсе и техкартах — обозначения по выбранному методическому документу:
  • ГОСТ Р 50.05.07-2018 — черт. 2, 3а–3и (прил. Г);
  • ГОСТ 7512-82 — черт. 4, 5а–5з, 6 (подлинная нумерация ГОСТ 7512).
"""

from django.templatetags.static import static


# ------------------------------------------------------------------
# ГОСТ Р 50.05.07-2018 (прил. Г) — отображаемые имена
# ------------------------------------------------------------------
SCHEME_CHOICES = [
    ('',     '— Выберите схему просвечивания —'),
    ('4_6',  'Чертёж 2 — Плоские детали, листы, обечайки'),
    ('5a',   'Чертёж 3а — Трубопровод Dн > 50 мм; плёнка внутри трубы'),
    ('5b',   'Чертёж 3б — Трубопровод Dн > 50 мм; плёнка внутри трубы'),
    ('5v',   'Чертёж 3в — Трубопровод Dн ≤ 100 мм; просвечивание на эллипс'),
    ('5g',   'Чертёж 3г — Трубопровод Dн > 50 мм; плёнка снаружи'),
    ('5d',   'Чертёж 3д — Трубопровод Dн > 50 мм; плёнка снаружи'),
    ('5zh',  'Чертёж 3ж — Трубопровод Dн ≤ 2000 мм; панорамное'),
    ('5z',   'Чертёж 3и — Трубопровод Dн > 2000 мм; плёнка снаружи'),
]

SCHEME_HELP_TEXT = (
    'Выберите схему по типу объекта. '
    'Для трубопроводов — чертежи 3а–3и. Для плоских деталей — Чертёж 2.'
)

FLAT_OBJECT_SCHEMES = ('4_6',)
PIPE_OBJECT_SCHEMES = ('5a', '5b', '5v', '5g', '5d', '5zh', '5z')

SCHEME_USER_LABELS = {
    '4_6': 'Чертёж 2 — плоские детали',
    '5a':  'Чертёж 3а — трубопровод Dн > 50 мм',
    '5b':  'Чертёж 3б — трубопровод Dн > 50 мм',
    '5v':  'Чертёж 3в — трубопровод Dн ≤ 100 мм',
    '5g':  'Чертёж 3г — трубопровод Dн > 50 мм',
    '5d':  'Чертёж 3д — трубопровод Dн > 50 мм',
    '5zh': 'Чертёж 3ж — панорамное, Dн ≤ 2000 мм',
    '5z':  'Чертёж 3и — трубопровод Dн > 2000 мм',
    '5e':  'Чертёж 3е',
}

SCHEME_DESCRIPTIONS = {
    '4_6': 'Плоские детали и листы. Просвечивание через одну стенку.',
    '5a':  'Трубопровод Dн > 50 мм. Плёнка внутри трубы.',
    '5b':  'Трубопровод Dн > 50 мм. Плёнка внутри трубы.',
    '5v':  'Трубопровод малого диаметра (Dн ≤ 100 мм). Просвечивание на эллипс.',
    '5g':  'Трубопровод Dн > 50 мм. Плёнка снаружи.',
    '5d':  'Трубопровод Dн > 50 мм. Плёнка снаружи.',
    '5zh': 'Панорамное просвечивание. Dн ≤ 2 м. Одна экспозиция на весь периметр.',
    '5z':  'Трубопровод большого диаметра (Dн > 2 м).',
}

SCHEME_IMAGES = {
    '4_6':  'img/scheme_4_6.png',
    '5a':   'img/scheme_5a.png',
    '5b':   'img/scheme_5b.png',
    '5v':   'img/scheme_5v.png',
    '5g':   'img/scheme_5g.png',
    '5d':   'img/scheme_5d.png',
    '5zh':  'img/scheme_5zh.png',
    '5z':   'img/scheme_5z.png',
}

SCHEME_DOCX_IMAGES = {
    '5v': 'img/scheme_5v_docx.jpg',
    '5g': 'img/scheme_5g_docx.jpg',
    '5d': 'img/scheme_5d_docx.jpg',
}

SCHEME_CARD_NAMES = {
    '4_6': 'Чертёж 2',
    '5a':  'Чертёж 3а',
    '5b':  'Чертёж 3б',
    '5v':  'Чертёж 3в',
    '5g':  'Чертёж 3г',
    '5d':  'Чертёж 3д',
    '5zh': 'Чертёж 3ж',
    '5z':  'Чертёж 3и',
    '5e':  'Чертёж 3е',
}

SCHEME_CARD_DESCRIPTIONS = {
    '4_6': 'Плоские детали, листы, обечайки.',
    '5a':  'Трубопровод Dн > 50 мм. Плёнка внутри трубы.',
    '5b':  'Трубопровод Dн > 50 мм. Плёнка внутри трубы.',
    '5v':  'Трубопровод Dн ≤ 100 мм. Просвечивание на эллипс.',
    '5g':  'Трубопровод Dн > 50 мм. Плёнка снаружи.',
    '5d':  'Трубопровод Dн > 50 мм. Плёнка снаружи.',
    '5zh': 'Трубопровод Dн ≤ 2000 мм. Панорамное просвечивание.',
    '5z':  'Трубопровод Dн > 2000 мм. Плёнка снаружи.',
    '5e':  'Специальная схема просвечивания.',
}

DOCX_BODY_TEXT_WIDTH_MM = 180.0

SCHEME_DOCX_IMAGE_CAPTION = {
    '5v': 'Схема 3 в по ГОСТ Р 50.05.07-2018',
    '5g': 'Схема 3 г по ГОСТ Р 50.05.07-2018',
    '5d': 'Схема 3 д по ГОСТ Р 50.05.07-2018',
}

# ------------------------------------------------------------------
# ГОСТ 7512-82 — подлинная нумерация чертежей
# (внутр. 5zh ≈ черт. 5е панорама; 5z ≈ черт. 5з; 5e ≈ черт. 5ж)
# ------------------------------------------------------------------
SCHEME_CHOICES_7512 = [
    ('',     '— Выберите схему просвечивания —'),
    ('4_6',  'Черт. 4 — Плоские детали, листы, обечайки'),
    ('5a',   'Черт. 5а — Плёнка внутри; Dн > 50 мм'),
    ('5b',   'Черт. 5б — Плёнка внутри; Dн > 50 мм'),
    ('5v',   'Черт. 5в — Две стенки; Dн ≤ 100 мм'),
    ('5g',   'Черт. 5г — Две стенки; Dн > 50 мм'),
    ('5d',   'Черт. 5д — Две стенки; Dн > 50 мм'),
    ('5zh',  'Черт. 5е — Панорамное; Dн ≤ 2000 мм (или 100% при Dн ≥ 2 м)'),
    ('5z',   'Черт. 5з — Выборочный контроль; Dн ≥ 2000 мм'),
]

SCHEME_USER_LABELS_7512 = {
    '4_6': 'Черт. 4 — плоские детали',
    '5a':  'Черт. 5а — трубопровод, плёнка внутри',
    '5b':  'Черт. 5б — трубопровод, плёнка внутри',
    '5v':  'Черт. 5в — две стенки, Dн ≤ 100 мм',
    '5g':  'Черт. 5г — две стенки, Dн > 50 мм',
    '5d':  'Черт. 5д — две стенки, Dн > 50 мм',
    '5zh': 'Черт. 5е — панорамное, Dн ≤ 2000 мм',
    '5z':  'Черт. 5з — выборочный, Dн ≥ 2000 мм',
    '5e':  'Черт. 5ж — панорамное (если 5е невозможно)',
}

SCHEME_CARD_NAMES_7512 = {
    '4_6': 'Черт. 4',
    '5a':  'Черт. 5а',
    '5b':  'Черт. 5б',
    '5v':  'Черт. 5в',
    '5g':  'Черт. 5г',
    '5d':  'Черт. 5д',
    '5zh': 'Черт. 5е',
    '5z':  'Черт. 5з',
    '5e':  'Черт. 5ж',
}

SCHEME_DESCRIPTIONS_7512 = {
    '4_6': 'Плоские детали и листы (черт. 4 ГОСТ 7512-82). Одна стенка.',
    '5a':  'Одна стенка: источник снаружи, плёнка внутри (черт. 5а).',
    '5b':  'Одна стенка: источник снаружи, плёнка внутри (черт. 5б).',
    '5v':  'Две стенки; рекомендуется для Dн до 100 мм (черт. 5в).',
    '5g':  'Две стенки; для изделий диаметром более 50 мм (черт. 5г).',
    '5d':  'Две стенки; для изделий диаметром более 50 мм (черт. 5д).',
    '5zh': (
        'Панорамное просвечивание (черт. 5е): Dн до 2 м при любом объёме; '
        'при Dн ≥ 2 м — при 100%-ном контроле.'
    ),
    '5z':  'Выборочный контроль изделий диаметром 2 м и более (черт. 5з).',
}

SCHEME_CARD_DESCRIPTIONS_7512 = dict(SCHEME_DESCRIPTIONS_7512)

SCHEME_DOCX_IMAGE_CAPTION_7512 = {
    '5v': 'Схема черт. 5в по ГОСТ 7512-82',
    '5g': 'Схема черт. 5г по ГОСТ 7512-82',
    '5d': 'Схема черт. 5д по ГОСТ 7512-82',
}

_SCHEME_LABELS = dict(SCHEME_CHOICES)
_SCHEME_LABELS_7512 = dict(SCHEME_CHOICES_7512)


def _style(doc_code: str | None = None, style: str | None = None) -> str:
    if style in ('7512', '50_05_07'):
        return style
    if doc_code:
        from techcards.methodology import get_methodology
        return get_methodology(doc_code).scheme_label_style
    return '50_05_07'


def get_schemes_for_object_type(object_type: str) -> tuple[str, ...]:
    """Внутренние коды схем, допустимых для типа объекта контроля."""
    if object_type == 'pipe':
        return PIPE_OBJECT_SCHEMES
    if object_type in ('flat', 'vessel'):
        return FLAT_OBJECT_SCHEMES
    return tuple(code for code, _ in SCHEME_CHOICES if code)


def get_scheme_choices_for_object_type(
    object_type: str,
    doc_code: str | None = None,
) -> list[tuple[str, str]]:
    """Выпадающий список схем с учётом типа объекта и методики."""
    codes = get_schemes_for_object_type(object_type)
    labels = _SCHEME_LABELS_7512 if _style(doc_code) == '7512' else _SCHEME_LABELS
    choices = [('', '— Выберите схему просвечивания —')]
    for code in codes:
        choices.append((code, labels.get(code, code)))
    return choices


def get_scheme_docx_image_rel(scheme_code: str, scheme_info: dict | None = None) -> str:
    """Относительный путь к схеме для п. 6.9 DOCX."""
    info = scheme_info or {}
    if scheme_code in SCHEME_DOCX_IMAGES:
        return SCHEME_DOCX_IMAGES[scheme_code]
    if info.get('docx_image'):
        return info['docx_image']
    return info.get('image') or SCHEME_IMAGES.get(scheme_code, '')


def _emu_to_mm(emu: int) -> float:
    return emu / 914400 * 25.4


def get_docx_body_width_mm(doc) -> float:
    """Ширина текстовой области DOCX (= ширина верхнего колонтитула)."""
    sec = doc.sections[0]
    return round(_emu_to_mm(sec.page_width - sec.left_margin - sec.right_margin), 1)


def get_scheme_docx_image_width(scheme_code: str, doc=None) -> float:
    """Ширина подробной схемы в DOCX: на всю ширину текстовой области."""
    if scheme_code not in SCHEME_DOCX_IMAGES:
        return 45.0
    if doc is not None:
        return get_docx_body_width_mm(doc)
    return DOCX_BODY_TEXT_WIDTH_MM


def get_scheme_card_name(scheme_code: str, doc_code: str | None = None) -> str:
    if _style(doc_code) == '7512':
        return SCHEME_CARD_NAMES_7512.get(scheme_code, scheme_code)
    return SCHEME_CARD_NAMES.get(scheme_code, scheme_code)


def get_scheme_docx_caption(
    scheme_code: str,
    scheme_info: dict | None = None,
    doc_code: str | None = None,
) -> str:
    """Подпись под изображением схемы в п. 6.9."""
    if _style(doc_code) == '7512':
        if scheme_code in SCHEME_DOCX_IMAGE_CAPTION_7512:
            return SCHEME_DOCX_IMAGE_CAPTION_7512[scheme_code]
        name = SCHEME_CARD_NAMES_7512.get(scheme_code, '')
        desc = SCHEME_CARD_DESCRIPTIONS_7512.get(scheme_code, '')
        return ' '.join(filter(None, [name, desc])).strip()

    if scheme_code in SCHEME_DOCX_IMAGE_CAPTION:
        return SCHEME_DOCX_IMAGE_CAPTION[scheme_code]
    info = scheme_info or {}
    name = info.get('name') or SCHEME_CARD_NAMES.get(scheme_code, '')
    desc = info.get('description') or SCHEME_CARD_DESCRIPTIONS.get(scheme_code, '')
    return ' '.join(filter(None, [name, desc])).strip()


def get_scheme_user_label(code: str, doc_code: str | None = None) -> str:
    """Пользовательское название схемы по внутреннему коду."""
    if _style(doc_code) == '7512':
        return SCHEME_USER_LABELS_7512.get(code, code)
    return SCHEME_USER_LABELS.get(code, code)


def get_scheme_ui_data(doc_code: str | None = None) -> dict:
    """Данные для JavaScript на шаге 3: изображения и описания."""
    descs = SCHEME_DESCRIPTIONS_7512 if _style(doc_code) == '7512' else SCHEME_DESCRIPTIONS
    return {
        code: {
            'img': static(path),
            'desc': descs.get(code, ''),
            'label': get_scheme_user_label(code, doc_code),
            'card_name': get_scheme_card_name(code, doc_code),
        }
        for code, path in SCHEME_IMAGES.items()
    }


def resolve_scheme_info_for_display(scheme_code: str, doc_code: str | None = None) -> dict:
    """Словарь name/description для генератора (под выбранную методику)."""
    from normative.calculations import SCHEME_INFO
    base = dict(SCHEME_INFO.get(scheme_code, {}))
    if _style(doc_code) == '7512':
        base['name'] = SCHEME_CARD_NAMES_7512.get(scheme_code, base.get('name', ''))
        base['description'] = SCHEME_CARD_DESCRIPTIONS_7512.get(
            scheme_code, base.get('description', ''),
        )
        base['gost_drawing'] = SCHEME_CARD_NAMES_7512.get(scheme_code, '')
        base['standard'] = 'ГОСТ 7512-82'
    else:
        base['gost_drawing'] = SCHEME_CARD_NAMES.get(scheme_code, '')
        base['standard'] = 'ГОСТ Р 50.05.07-2018'
    return base
