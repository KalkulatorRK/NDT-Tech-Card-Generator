"""Синхронизация структурированных НД (normative/*.py) в базу ИИ-консультанта.

Проблема: в PDF многие таблицы НД — это картинки без текстового слоя,
поэтому OCR их не захватывает, и консультант отвечает по неполным данным
(или путает таблицы, как было с K=0,30 вместо 0,20).

Решение: модули normative/*.py содержат те же таблицы в виде списков/словарей.
Этот скрипт извлекает ключевые справочные таблицы и добавляет их в базу
консультанта как ЭТАЛОННЫЕ чанки (идемпотентно — дубли по section_label игнорируются).

Запуск:
    python3 sync_normative_py_to_db.py
"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ndt_project.settings')
os.environ['ALLOWED_HOSTS'] = 'testserver,127.0.0.1,localhost'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from ai_consultant.models import DocumentSource, DocumentChunk
from ai_consultant.services.embeddings import embed_texts, get_embedding_model_name

# Map документ-код НД -> doc_number в базе консультанта
DOC_MAP = {
    'НП-105-18': 'НП-105-18',
    'ГОСТ Р 50.05.07-2018': 'ГОСТ Р 50.05.07-2018',
    'ГОСТ Р 50.05.09-2018': 'ГОСТ Р 50.05.09-2018',
    'НП-104-18': 'НП-104-18',
    'ГОСТ 7512-82': 'ГОСТ 7512-82',
    'ГОСТ Р 59023.2-2020': 'ГОСТ Р 59023.2-2020',
    'СНиП 3.05.05-84': 'СНиП 3.05.05-84',
}

PREFIX = ''  # префикс убран: в выдаче нужны только строгие ссылки НД+пункт


def _norm_label(raw):
    """Убирает служебные префиксы, оставляя только ссылку НД+пункт/таблица."""
    s = raw.replace('ЭТАЛОН', '').strip()
    return s


def _get_or_create_source(doc_number, title, doc_type):
    # устойчиво к дубликатам (docx-ингест + .py-синх могут создать 2 source)
    existing = DocumentSource.objects.filter(doc_number=doc_number).first()
    if existing:
        return existing
    src, _ = DocumentSource.objects.get_or_create(
        doc_number=doc_number,
        defaults={'title': title, 'doc_type': doc_type},
    )
    return src


def _next_index(src):
    return DocumentChunk.objects.filter(source=src).count()


def _add_chunks(src, specs, doc_number=None):
    """specs: list of (section_label, text). Идемпотентно.
    doc_number — если задан, дописывается в начало section_label
    (чтобы ссылка была самодостаточной: 'НД, пункт/таблица')."""
    existing = set(
        DocumentChunk.objects.filter(source=src)
        .values_list('section_label', flat=True)
    )
    new = []
    for lbl, txt in specs:
        full = f"{doc_number}, {_norm_label(lbl)}" if doc_number else _norm_label(lbl)
        if full not in existing:
            new.append((full, txt))
    if not new:
        print(f"  (все {len(specs)} чанков уже есть, пропуск)")
        return
    texts = [t for _, t in new]
    vecs = embed_texts(texts)
    base = _next_index(src)
    for i, (lbl, txt) in enumerate(new):
        DocumentChunk.objects.create(
            source=src,
            chunk_index=base + i,
            section_label=lbl,
            text=txt,
            embedding=vecs[i],
            embedding_model_version=get_embedding_model_name(),
        )
    print(f"  добавлено {len(new)} чанков")


def _build_np105():
    from normative import np_105_18 as M
    src = DocumentSource.objects.filter(doc_number=DOC_MAP['НП-105-18']).first()
    if not src:
        print("НП-105-18 нет в базе, пропуск")
        return
    print("НП-105-18:")
    # Таблица 4.8 (РГК) — категории I/II/III, сталь
    tables = [('I', M.TABLE_4_8_CAT_I), ('II', M.TABLE_4_8_CAT_II), ('III', M.TABLE_4_8_CAT_III)]
    specs = []
    for cat, rows in tables:
        for r in rows:
            tmin, tmax, K, vincl, vclust, n, S, kr_s, kr_w, kr_n = r
            lbl = f"{PREFIX} 4.8 РГК {cat} {tmin:g}-{tmax:g}мм"
            txt = (
                f"НП-105-18, Таблица 4.8 (РАДИОГРАФИЧЕСКИЙ КОНТРОЛЬ, РГК), категория {cat}, сталь. "
                f"При номинальной толщине свариваемых деталей от {tmin:g} до {tmax:g} мм "
                f"требуемая чувствительность контроля K = {K:g} мм (не более). "
                f"Допустимые одиночные включения: размер не более {vincl:g} мм; "
                f"скопления — не более {vclust:g} мм; количество на 100 мм шва не более {n} шт; "
                f"суммарная приведённая площадь Sпр не более {S:g} мм²."
            )
            specs.append((lbl, txt))
    # Таблица 4.9 (Iн, IIн)
    for cat, rows in [('Iн', M.TABLE_4_9_CAT_IN), ('IIн', M.TABLE_4_9_CAT_IIN)]:
        for r in rows:
            tmin, tmax, K, mx, n, S = r
            lbl = f"{PREFIX} 4.9 РГК {cat} {tmin:g}-{tmax:g}мм"
            if mx is None:
                txt = (f"НП-105-18, Таблица 4.9, категория {cat}, толщина {tmin:g}–{tmax:g} мм: "
                       f"дефекты НЕ ДОПУСКАЮТСЯ (K={K:g} мм).")
            else:
                txt = (f"НП-105-18, Таблица 4.9 (РГК), категория {cat}. "
                       f"При толщине {tmin:g}–{tmax:g} мм требуемая чувствительность K = {K:g} мм; "
                       f"макс. размер включения {mx:g} мм; количество на 100 мм — {n} шт; "
                       f"Sпр не более {S:g} мм².")
            specs.append((lbl, txt))
    _add_chunks(src, specs, doc_number=DOC_MAP['НП-105-18'])


def _build_gost500507():
    from normative import gost_50_05_07 as M
    src = DocumentSource.objects.filter(doc_number=DOC_MAP['ГОСТ Р 50.05.07-2018']).first()
    if not src:
        print("ГОСТ Р 50.05.07-2018 нет в базе, пропуск")
        return
    print("ГОСТ Р 50.05.07-2018:")
    specs = []
    # Таблица Б.1 — диапазоны применимости источников по толщинам
    for material, ranges in M.TABLE_B_SOURCE_RANGES.items():
        for (tmin, tmax, codes, films) in ranges:
            lbl = f"{PREFIX} Б.1 {material} {tmin}-{tmax}мм"
            txt = (
                f"ГОСТ Р 50.05.07-2018, таблица Б.1 (приложение Б): для материала «{material}» "
                f"при толщине от {tmin} до {tmax} мм допустимые источники излучения: "
                f"{', '.join(codes)}; рекомендуемые плёнки: {', '.join(films)}."
            )
            specs.append((lbl, txt))
    # Классы плёнок
    for f in M.FILM_CLASSES:
        lbl = f"{PREFIX} плёнка {f['class']}"
        allowed = ', '.join(f.get('allowed_for', [])) or '—'
        txt = (f"ГОСТ Р 50.05.07-2018: класс плёнки {f['class']} — {f.get('description','')}. "
               f"Примеры: {f.get('examples','')}. "
               f"Мин. оптическая плотность: {f.get('optical_density_min','')}. "
               f"Допускается для категорий: {allowed}.")
        specs.append((lbl, txt))
    # Экраны
    for key, val in M.SCREEN_REQUIREMENTS.items():
        lbl = f"{PREFIX} экран {key}"
        txt = f"ГОСТ Р 50.05.07-2018, требования к экранам ({key}): {val}."
        specs.append((lbl, txt))
    _add_chunks(src, specs, doc_number=DOC_MAP['ГОСТ Р 50.05.07-2018'])


def _build_np104():
    from normative import np_104_18 as M
    src = _get_or_create_source(
        DOC_MAP['НП-104-18'],
        'НП-104-18 Правила контроля металла и сварных соединений (категории, методы НК)',
        'np',
    )
    print("НП-104-18:")
    specs = []
    for code, info in M.WELD_CATEGORIES.items():
        lbl = f"категория {code}"
        txt = (f"НП-104-18: категория сварного соединения {code} — {info.get('name','')}. "
               f"{info.get('description','')} Объём контроля: {info.get('control_volume')}%. "
               f"Примеры: {', '.join(info.get('examples', []))}.")
        specs.append((lbl, txt))
    for code, methods in M.REQUIRED_METHODS_BY_CATEGORY.items():
        lbl = f"методы НК кат. {code}"
        txt = (f"НП-104-18, п. 4: для сварных соединений категории {code} обязательные методы "
               f"неразрушающего контроля: {', '.join(methods)}.")
        specs.append((lbl, txt))
    specs.append((
        f"титан зачистка",
        f"НП-104-18, п. 84: ширина зачищенных участков кромок титановых сплавов — "
        f"не менее {M.TITANIUM_EDGE_CLEANING_WIDTH_ARC_MM:g} мм (дуговая сварка/наплавка), "
        f"не менее {M.TITANIUM_EDGE_CLEANING_WIDTH_ESW_MM:g} мм (электрошлаковая сварка).",
    ))
    _add_chunks(src, specs, doc_number=DOC_MAP['НП-104-18'])


def _build_gost7512():
    from normative import gost_7512 as M
    src = _get_or_create_source(
        DOC_MAP['ГОСТ 7512-82'],
        'ГОСТ 7512-82 Проволочные эталоны чувствительности (ИКИ), запись дефектов',
        'gost',
    )
    print("ГОСТ 7512-82:")
    specs = []
    # ОДИН сводный чанк по табл. 2 (все эталоны и диаметры) — чтобы LLM цитировал
    # ровно [ГОСТ 7512-82, табл. 2], без перечисления эталонов в скобках.
    lines = []
    for set_no, wires in M.WIRE_IQI_SETS.items():
        max_t = M.SET_THICKNESS_MAX_MM.get(set_no)
        rows = "; ".join(f"проволока {n} — Ø {d:g} мм" for n, d in wires)
        lines.append(f"Эталон №{set_no} (до {max_t:g} мм): {rows}.")
    overview = (
        f"ГОСТ 7512-82, таблица 2: проволочные эталоны чувствительности. "
        f"Всего 4 типоразмера эталонов (№1–№4), в каждом типоразмере 7 проволок. "
        f"{' '.join(lines)}"
    )
    specs.append(("табл. 2 (проволочные эталоны)", overview))
    for mat, code in M.IQI_MATERIAL_CODES.items():
        lbl = f"п. 2.13, код материала {code}"
        txt = (f"ГОСТ 7512-82, п. 2.13: код материала эталона {code} — {mat} "
               f"({M.IQI_MATERIAL_LABELS.get(code,'')}). Маркировка ИКИ: {code} + номер эталона.")
        specs.append((lbl, txt))
    _add_chunks(src, specs, doc_number=DOC_MAP['ГОСТ 7512-82'])


def _build_gost59023():
    from normative import gost_59023_2 as M
    src = _get_or_create_source(
        DOC_MAP['ГОСТ Р 59023.2-2020'],
        'ГОСТ Р 59023.2-2020 Сварные соединения. Типы, процессы сварки',
        'gost',
    )
    print("ГОСТ Р 59023.2-2020:")
    specs = []
    for code, info in M.WELDING_PROCESSES.items():
        lbl = f"{PREFIX} 59023 процесс {code}"
        txt = (f"ГОСТ Р 59023.2-2020: сварочный процесс {code} — {info.get('name','')} "
               f"(обозначение: {info.get('abbr','')}, ISO: {info.get('iso_ref','')}).")
        specs.append((lbl, txt))
    _add_chunks(src, specs, doc_number=DOC_MAP['ГОСТ Р 59023.2-2020'])


def _build_fact_guards():
    """Разъясняющие эталоны-факты: защита от ловушек и ошибок формулировок.
    Дают LLM фактологическую базу для аргументированного отказа, а не 'нет данных'."""
    print("Факт-охранники:")
    specs = [
        (
            "категории НП-105-18 (справочно)",
            "НП-105-18: таблица 4.8 (радиографический контроль, РГК) устанавливает требуемую "
            "чувствительность K для сварных соединений категорий I, II, III (сталь), а также "
            "Iн, IIн. Категории IV в таблице 4.8 НП-105-18 НЕТ — для неё РГК не применяется "
            "и требование чувствительности K не назначается.",
        ),
        (
            "методы НК кат. IV (НП-104-18)",
            "НП-104-18, п. 4: для сварных соединений категории IV обязательный метод "
            "неразрушающего контроля — только ВИК (визуальный и измерительный). "
            "Радиографический (РГК) и ультразвуковой (УЗК) контроль для категории IV "
            "не применяются, поэтому требование чувствительности K по НП-105-18 к ней не относится.",
        ),
        (
            "чувствительность K — источник",
            "НП-105-18: требуемая чувствительность контроля K определяется ТОЛЬКО по таблицам "
            "4.8 (категории I, II, III) и 4.9 (Iн, IIн). Для других категорий и материалов "
            "значение K берётся из соответствующей таблицы (4.10 — алюминий, 4.11 — титан). "
            "Если категория или толщина не входят ни в одну строку таблиц — значение K не установлено.",
        ),
    ]
    # привязываем к НП-105-18 как к основному документу по K
    src = _get_or_create_source(
        DOC_MAP['НП-105-18'],
        'НП-105-18 Правила контроля металла и трубопроводов АЭУ',
        'np',
    )
    _add_chunks(src, specs, doc_number=DOC_MAP['НП-105-18'])


def _build_from_rtf():
    """Ингест связного текста пунктов из RTF-исходников (normative_docs/*.rtf).
    Закрывает нарративные вопросы, которые не попали в структурированные .py
    (канавочный эталон, перекрытие снимков, околошовная зона и т.п.).
    Дубли с уже загруженными PDF не создаются (проверка по section_label)."""
    from pathlib import Path
    from ai_consultant.services.ingestion import parse_rtf_to_sections
    nd_dir = Path(__file__).resolve().parent / 'normative_docs'
    # сопоставление файлов RTF -> doc_number
    rtf_map = {
        'ГОСТ Р 50.05.07-18.rtf': DOC_MAP['ГОСТ Р 50.05.07-2018'],
        'ГОСТ Р 59023.2-2020': DOC_MAP['ГОСТ Р 59023.2-2020'],
    }
    total = 0
    for fname, doc_number in rtf_map.items():
        fpath = nd_dir / fname
        if not fpath.exists():
            print(f"RTF не найден: {fpath}")
            continue
        print(f"RTF: {fname}")
        raw = fpath.read_bytes()
        sections = parse_rtf_to_sections(raw)
        sections = [s for s in sections if len(s['text'].strip()) > 20]
        src = _get_or_create_source(
            doc_number,
            doc_number,
            'gost' if 'ГОСТ' in doc_number else 'np',
        )
        _add_chunks(src, [(s['section_label'], s['text']) for s in sections],
                    doc_number=doc_number)
        total += len(sections)
    _add_chunks(src, specs, doc_number=DOC_MAP['ГОСТ 7512-82'])


def _build_gost7512_full():
    """Полный текст ГОСТ 7512-82 из .py (не только таблицы, но и описания пунктов):
    маркировка ИКИ (п. 2.13), выбор типоразмера (табл. 2), условные
    обозначения материала. Закрывает нарративные вопросы (напр. «что обозначает
    первая цифра маркировки ИКИ»), которые не покрыты одними таблицами."""
    from normative import gost_7512 as G
    specs = [
        (
            "7512-82, п. 2.13 — маркировка ИКИ",
            "Маркировка проволочного ИКИ состоит из 2–3 цифр. Первая цифра "
            "обозначает материал эталона (1 — сплавы на основе железа, "
            "2 — алюминий и магний, 3 — титан, 4 — медь, 5 — никель). "
            "Следующие 1–2 цифры — номер эталона (1–4). Примеры маркировки: 11, 12, 14. "
            "Стандарт: ГОСТ 7512-82, п. 2.13.",
        ),
        (
            "7512-82, табл. 2 — выбор типоразмера ИКИ",
            "Номер типоразмера проволочного эталона (1–4) выбирается по радиационной "
            "толщине в месте установки ИКИ: типоразмер 1 — до 12 мм, 2 — до 25 мм, "
            "3 — до 140 мм, 4 — до 400 мм. Каждый типоразмер содержит 7 проволок. "
            "Стандарт: ГОСТ 7512-82, табл. 2.",
        ),
        (
            "7512-82, п. 2.13 — коды материала ИКИ",
            "Коды материала эталона: 1 — сплавы на основе железа (steel), "
            "2 — алюминий и магний (aluminum), 3 — титан (titanium), "
            "4 — медь (copper), 5 — никель (nickel). Используются в маркировке ИКИ. "
            "Стандарт: ГОСТ 7512-82, п. 2.13.",
        ),
        (
            "7512-82 — назначение проволочных ИКИ",
            "Проволочные эталоны чувствительности (ИКИ) применяются при радиографическом "
            "контроле для оценки чувствительности по ГОСТ 7512-82. Чувствительность "
            "контроля K определяется по табл. 2 (7 проволок в каждом из 4 типоразмеров).",
        ),
        (
            "7512-82, п. 3.9 — канавочный (режущий) эталон",
            "Согласно ГОСТ 7512-82 п. 3.9, канавочный (режущий) эталон применяется для "
            "оценки чувствительности радиографического контроля методом сравнения "
            "изображения канавки с изображением дефекта. Эталон изготавливается из "
            "материала, близкого по поглощающей способности к контролируемому изделию. "
            "[ТРЕБУЕТСЯ СВЕРКА С ОРИГИНАЛОМ НД ДЛЯ ТОЧНОЙ ФОРМУЛИРОВКИ П. 3.9 — ТЕКСТ "
            ".doc НЕДОСТУПЕН]. Дополняет ГОСТ Р 50.05.07-2018 п. 6.1.16 (установка "
            "канавочного эталона на трубопроводе Dн ≤ 100 мм вдоль оси трубы).",
        ),
    ]
    src = _get_or_create_source(
        DOC_MAP['ГОСТ 7512-82'],
        'ГОСТ 7512-82 Проволочные эталоны чувствительности (ИКИ)',
        'gost',
    )
    _add_chunks(src, specs, doc_number=DOC_MAP['ГОСТ 7512-82'])


def _build_np104_full():
    """Доп. текст НП-104-18 из .py: околошовная зона (ОШЗ), зачистка кромок."""
    from normative import np_104_18 as M
    from normative import gost_59023_2 as G
    specs = [
        (
            "НП-104-18, околошовная зона (ОШЗ) для РГК",
            f"Ширина околошовной зоны (ОШЗ) при радиографическом контроле "
            f"сварных соединений по ГОСТ Р 59023.2-2020 составляет не менее "
            f"{G.HAZ_WIDTH_MM:g} мм. Для титановых сплавов ширина зачищенных "
            f"участков кромок (НП-104-18, п. 84): не менее "
            f"{M.TITANIUM_EDGE_CLEANING_WIDTH_ARC_MM:g} мм (дуговая сварка/наплавка), "
            f"не менее {M.TITANIUM_EDGE_CLEANING_WIDTH_ESW_MM:g} мм "
            f"(электрошлаковая сварка). Контролируемая зона включает само "
            f"сварное соединение и прилегающие участки основного металла.",
        ),
        (
            "НП-104-18, п. 84 — зачистка кромок титана",
            f"НП-104-18, п. 84: ширина зачищенных участков кромок титановых "
            f"сплавов до наложения шва — не менее {M.TITANIUM_EDGE_CLEANING_WIDTH_ARC_MM:g} мм "
            f"(дуговые процессы), не менее {M.TITANIUM_EDGE_CLEANING_WIDTH_ESW_MM:g} мм "
            f"(электрошлаковая сварка).",
        ),
    ]
    src = _get_or_create_source(
        DOC_MAP['НП-104-18'],
        'НП-104-18 Правила контроля сварных соединений',
        'np',
    )
    _add_chunks(src, specs, doc_number=DOC_MAP['НП-104-18'])


def _build_gost500507_full():
    """Доп. текст ГОСТ Р 50.05.07-2018 из .py: типы эталонов (канавочный и др.)."""
    from normative import gost_50_05_07 as G
    lines = []
    for iqi in G.IQI_TYPES:
        lines.append(f"{iqi['name']} (код {iqi['code']}): стандарт {iqi['standard']}, "
                     f"предпочтителен для категорий {', '.join(iqi['preferred_for'])}.")
    txt = ("ГОСТ Р 50.05.07-2018, эталоны чувствительности (ИКИ): "
           + " ".join(lines) + " Канавочный (режущий) эталон применяется для оценки "
           "чувствительности методом сравнения изображения канавки с изображением "
           "дефекта; устанавливается на трубопроводе Dн ≤ 100 мм вдоль оси трубы "
           "(ГОСТ Р 50.05.07-2018, п. 6.1.16).")
    specs = [("ГОСТ Р 50.05.07-2018, типы эталонов ИКИ", txt)]
    src = _get_or_create_source(
        DOC_MAP['ГОСТ Р 50.05.07-2018'],
        'ГОСТ Р 50.05.07-2018 Контроль неразрушающий. Сварка и родственные процессы',
        'gost',
    )
    _add_chunks(src, specs, doc_number=DOC_MAP['ГОСТ Р 50.05.07-2018'])


def _build_gost500509():
    """Эталонные чанки ГОСТ Р 50.05.09-2018 (капиллярный контроль) из .py."""
    from normative import gost_50_05_09 as M
    src = _get_or_create_source(
        DOC_MAP['ГОСТ Р 50.05.09-2018'],
        M.DOCUMENT_FULL_NAME,
        'gost',
    )
    print("ГОСТ Р 50.05.09-2018:")
    specs = [
        ("табл. 1 классы чувствительности", M.format_sensitivity_table()),
        ("п. 5.5–5.6 условия среды", M.format_ambient_rules()),
        ("п. 6.1.1 наборы ДМ", M.format_dm_rules()),
        (
            "п. 6.2 персонал",
            f"{M.DOCUMENT_CODE}, п. 6.2: капиллярный контроль выполняет персонал, "
            f"квалификация которого подтверждена по {M.PERSONNEL_STANDARD}.",
        ),
        (
            "п. 8.1.5 шероховатость",
            f"{M.DOCUMENT_CODE}, п. 8.1.5: участки контроля обрабатывают до "
            f"Ra {M.SURFACE_ROUGHNESS_RA_TARGET} (Rz {M.SURFACE_ROUGHNESS_RZ_TARGET}). "
            f"Допускается Ra {M.SURFACE_ROUGHNESS_RA_MAX_ALLOWED} "
            f"(Rz {M.SURFACE_ROUGHNESS_RZ_MAX_ALLOWED}) без недопустимого окрашенного фона. "
            f"Образцы шероховатости — {M.SURFACE_ROUGHNESS_STANDARD}.",
        ),
        (
            "п. 8.2.1.1 время контакта пенетранта",
            f"{M.DOCUMENT_CODE}, п. 8.2.1.1: минимальное время контакта пенетранта — "
            f"не менее {M.PENETRANT_CONTACT_MIN_WELD_MIN} мин для сварных соединений "
            f"(включая околошовную зону) и не менее {M.PENETRANT_CONTACT_MIN_BASE_METAL_MIN} мин "
            f"для основного металла. Высыхание пенетранта на поверхности не допускается "
            f"(п. 8.2.1.2).",
        ),
        (
            "п. 8.3.2 осмотр после проявителя",
            f"{M.DOCUMENT_CODE}, п. 8.3.2: при отсутствии указаний производителя осмотр "
            f"проводят дважды — через {M.DEVELOPER_INSPECTION_FIRST_MIN[0]}–"
            f"{M.DEVELOPER_INSPECTION_FIRST_MIN[1]} мин после нанесения проявителя и через "
            f"{M.DEVELOPER_INSPECTION_SECOND_MIN} мин после его высыхания.",
        ),
        (
            "п. 5.1–5.4 общие положения КК",
            f"{M.DOCUMENT_CODE}, п. 5.1–5.4: капиллярный метод основан на проникновении "
            f"индикаторных жидкостей в поверхностные несплошности и регистрации индикаторных "
            f"следов. Контролируют поверхности, признанные годными по ВИК. КК проводят после "
            f"ВИК и перед другими методами НК (УЗК, МПД, РГК и др.).",
        ),
        (
            "п. 7.1–7.3 технологические карты",
            f"{M.DOCUMENT_CODE}, п. 7.1–7.3: контроль проводят по технологическим картам. "
            f"В карте указывают способ и класс чувствительности, набор ДМ, условия "
            f"(температура, влажность, освещённость), КО, подготовку поверхности, "
            f"шероховатость, последовательность операций и нормы оценки качества.",
        ),
    ]
    for code, row in M.ILLUMINANCE_LX.items():
        specs.append((
            f"табл. 2 освещённость класс {code}",
            f"{M.DOCUMENT_CODE}, табл. 2, класс {code}: люминесцентные лампы — "
            f"комбинированная {row['fluorescent_combined']} лк, общая "
            f"{row['fluorescent_general']} лк; накаливания — комбинированная "
            f"{row['incandescent_combined']} лк, общая {row['incandescent_general']} лк.",
        ))
    for code, uv in M.UV_IRRADIANCE_UW_PER_CM2.items():
        specs.append((
            f"табл. 3 УФ класс {code}",
            f"{M.DOCUMENT_CODE}, табл. 3, класс {code}: ультрафиолетовая облучённость "
            f"контролируемой поверхности — {uv} мкВт/см².",
        ))
    for kit in M.RECOMMENDED_DM_KITS:
        tmin, tmax = kit['temp_c']
        specs.append((
            f"прил. А набор {kit['name'][:40]}",
            f"{M.DOCUMENT_CODE}, приложение А, табл. А.1: набор «{kit['name']}», "
            f"способ {kit['method']}, температуры {tmin}…{tmax} °C, класс "
            f"{kit['class']}, верхний порог чувствительности: {kit['threshold_note']} мкм.",
        ))
    _add_chunks(src, specs, doc_number=DOC_MAP['ГОСТ Р 50.05.09-2018'])


def _build_snip_3050584():
    from normative import snip_3_05_05_84 as M
    src = DocumentSource.objects.filter(doc_number=DOC_MAP['СНиП 3.05.05-84']).first()
    if not src:
        print("СНиП 3.05.05-84 нет в базе, пропуск")
        return
    print("СНиП 3.05.05-84:")
    specs = []
    for code, info in M.PIPELINE_CATEGORIES.items():
        uc = info['undercut_allowed_mm']
        uc_txt = 'не допускаются' if uc <= 0 else f'не более {uc:g} мм'
        pre = (
            ' До РК/УЗК — МПД или КК шва и зоны +20 мм.'
            if info['pre_rt_surface_ndt'] else ''
        )
        specs.append((
            f"п. 4.11–4.13 кат. {code}",
            f"{M.DOCUMENT_CODE}: {info['name']}. Объём РК/УЗК {info['control_volume_pct']} % "
            f"(п. 4.11). Браковка при суммарном балле ≥ {info['reject_score_min']} (п. 4.12). "
            f"Чувствительность — класс {info['sensitivity_class_gost7512']} по ГОСТ 7512-82 "
            f"(п. 4.13). Подрезы: {uc_txt} (п. 4.10).{pre}",
        ))
    for score, rows in M.SCORE_TABLES.items():
        for tmin, tmax, w, L, cl, s100 in rows:
            tmax_s = f'{tmax:g}' if tmax is not None else '∞'
            specs.append((
                f"прил. 4 балл {score} t={tmin:g}-{tmax_s}",
                f"{M.DOCUMENT_CODE}, приложение 4, оценка в баллах: балл {score}, "
                f"толщина стенки {tmin:g}–{tmax_s} мм: ширина (диаметр) включения "
                f"не более {w:g} мм; длина не более {L:g} мм; скопление не более {cl:g} мм; "
                f"суммарная длина на любом участке 100 мм — не более {s100:g} мм. "
                f"Превышение норм балла 3 → балл 6. Включения ≤0,2 мм не учитывают "
                f"(прим. 1), если не образуют скопление или сетку.",
            ))
    specs.append((
        "п. 4.12 удвоение объёма",
        f"{M.DOCUMENT_CODE}, п. 4.12: при браковке стыка объём контроля у сварщика "
        f"удваивают; для категории III при балле 4 и категории IV при балле 5 стык "
        f"не исправляют, но объём удваивают; при повторном браке в удвоенном объёме — "
        f"100 % стыков сварщика; при браке на 100 % — отстранение сварщика.",
    ))
    _add_chunks(src, specs, doc_number=DOC_MAP['СНиП 3.05.05-84'])


if __name__ == '__main__':
    _build_np105()
    _build_gost500507()
    _build_gost500509()
    _build_np104()
    _build_gost7512()
    _build_gost59023()
    _build_snip_3050584()
    _build_fact_guards()
    print("СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА")
