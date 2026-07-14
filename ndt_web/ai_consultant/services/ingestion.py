"""
Парсинг документа (PDF/DOCX/RTF) в список смысловых фрагментов.

Разбиение ПО СТРУКТУРЕ документа (пункты, разделы), а не по фиксированной
длине символов — критично для точности цитирования. Длинный пункт НЕ рвётся
посередине: если он превышает лимит эмбеддинга, делится на под-части ВНУТРИ
того же пункта (метка 'п. X (ч. N)'), чтобы смысл и номер сохранялись.

Дополнительно: OCR каждой страницы (рисунки/таблицы/формулы) — извлечённый
текст добавляется как отдельный чанк 'Рисунок/таблица (стр. N)'.

Раздел 11 ТЗ.
"""
import re
import hashlib

# ---------------------------------------------------------------------------
# Общие хелперы
# ---------------------------------------------------------------------------

def _split_long_section(label: str, text: str, max_chars: int = 4000) -> list[dict]:
    """Делит длинный пункт НД на под-части, НЕ разрывая его смысл.
    Каждой под-части сохраняется номер пункта (метка 'п. X (ч. N)').
    Границы режутся по абзацам, чтобы не рвать предложения.
    """
    if len(text) <= max_chars:
        return [{"section_label": label, "text": text}]
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks, buf, part = [], "", 1
    for p in paragraphs:
        if len(buf) + len(p) > max_chars and buf:
            chunks.append({"section_label": f"{label} (ч. {part})", "text": buf})
            buf = p
            part += 1
        else:
            buf = (buf + "\n" + p) if buf else p
    if buf:
        chunks.append({"section_label": f"{label} (ч. {part})", "text": buf})
    return chunks


def _fallback_split_by_length(text: str, max_chars: int = 4000) -> list[dict]:
    """Если структура не распознана — делим по абзацам с ограничением длины."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks, buf, idx = [], "", 0
    for p in paragraphs:
        if len(buf) + len(p) > max_chars and buf:
            chunks.append({"section_label": f"фрагмент {idx}", "text": buf})
            buf = p
            idx += 1
        else:
            buf = (buf + "\n" + p) if buf else p
    if buf:
        chunks.append({"section_label": f"фрагмент {idx}", "text": buf})
    return [c for c in chunks if len(c["text"]) > 20]


def _collect_text(file_bytes: bytes) -> str:
    import pdfplumber
    import io
    parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def parse_pdf_to_sections(file_bytes: bytes, ocr_all: bool = False) -> list[dict]:
    """Возвращает список {"section_label": str, "text": str}.

    Текст страниц разбивается по пронумерованным пунктам НД (каждый пункт —
    отдельный чанк, длинные делятся на под-части внутри пункта).

    ОБРАБОТКА РИСУНКОВ/ТАБЛИЦ (vision):
    - каждая страница, содержащая рисунок/таблицу (по тексту) ИЛИ преимущественно
      графику (мало текста), рендерится и прогоняется через describe_image();
    - извлечённое описание (что нарисовано + текст + связь с НД) сохраняется как
      отдельный чанк "Рисунок/таблица N (стр. M)";
    - чанк рисунка СВЯЗЫВАЕТСЯ с пунктом, который его упоминает: в текст пункта
      дописывается "[См. рисунок N: <краткое описание>]", а в чанк рисунка —
      "Упоминается в п. X". Так консультант видит и картинку, и контекст.
    """
    import pdfplumber
    import io
    from .figure_ocr import describe_image

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        pages_text = []
        for page in pdf.pages:
            pages_text.append(page.extract_text() or "")

        sections: list[dict] = []
        combined_parts = []
        for page_num, page in enumerate(pdf.pages, start=1):
            page_text = pages_text[page_num - 1]
            combined_parts.append(page_text)
            has_figure_kw = bool(re.search(r'(рис\s*\.?|рисунок|таблиц)', page_text, re.I))
            mostly_graphic = len(page_text.strip()) < 200
            if not (has_figure_kw or mostly_graphic or ocr_all):
                continue
            try:
                img = page.to_image(resolution=150)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                vision_text = describe_image(buf.getvalue())
                if not vision_text:
                    continue
                # номера рисунков/таблиц на странице
                fig_nums = re.findall(r'(?:рисунок|рис\.?|таблица)\s*(\d+)', page_text, re.I)
                figs = sorted(set(fig_nums), key=lambda x: int(x) if x.isdigit() else 0)
                fig_label = figs[0] if figs else str(page_num)
                # связываем с пунктом: ищем упоминание рисунка в полном тексте
                linked_section = ""
                if figs:
                    for fn in figs:
                        m = re.search(rf'(?m)^\s*(\d+(?:\.\d+)+[а-я]?\.?)\s+.*?рис\.?\s*{fn}\b',
                                      "\n".join(combined_parts), re.I | re.S)
                        if m:
                            linked_section = m.group(1)
                            break
                prefix = f"Рисунок/таблица {fig_label} (стр. {page_num})"
                desc = vision_text
                if linked_section:
                    desc += f"\n\nУпоминается в п. {linked_section}."
                sections.append({"section_label": prefix, "text": desc})
                # дописываем в текст связанного пункта (если найден)
                if linked_section:
                    short = vision_text.split("\n")[0][:200]
                    sections.append({
                        "section_label": f"п. {linked_section} (связь с рис. {fig_label})",
                        "text": f"[См. рисунок/таблицу {fig_label} (стр. {page_num}): {short}]",
                    })
            except Exception as e:
                print(f"[PDF] OCR стр. {page_num} пропущен: {e}")

    combined = "\n".join(combined_parts)

    # Разбиение по номерам пунктов (ГОСТ/НП: "5.3.2", "5.2в", "Таблица 4", "Приложение А")
    section_pattern = re.compile(r'(?m)^(\d+(?:\.\d+)+[а-я]?\.?)\s+(.+)')
    matches = list(section_pattern.finditer(combined))

    if not matches:
        return sections + _fallback_split_by_length(combined)

    for i, m in enumerate(matches):
        label = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(combined)
        text = combined[start:end].strip()
        if len(text) > 20:
            sections.extend(_split_long_section(f"п. {label}", text))
    return sections


# ---------------------------------------------------------------------------
# DOCX
# ---------------------------------------------------------------------------

def parse_docx_to_sections(file_bytes: bytes) -> list[dict]:
    """Аналогично PDF, но для DOCX через python-docx."""
    from docx import Document
    import io

    doc = Document(io.BytesIO(file_bytes))
    full_text = "\n".join(p.text for p in doc.paragraphs)
    section_pattern = re.compile(r'(?m)^(\d+(?:\.\d+){1,4}\.?)\\s+(.+)')
    matches = list(section_pattern.finditer(full_text))
    if not matches:
        return _fallback_split_by_length(full_text)

    sections = []
    for i, m in enumerate(matches):
        label = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        text = full_text[start:end].strip()
        if len(text) > 20:
            sections.extend(_split_long_section(f"п. {label}", text))
    return sections


# ---------------------------------------------------------------------------
# RTF (ansi cp1251 + \\uN escapes)
# ---------------------------------------------------------------------------

def parse_rtf_to_sections(file_bytes: bytes) -> list[dict]:
    """RTF не имеет надёжной разметки заголовков; разбиваем по пунктам,
    предварительно декодировав ansicpg + \\uN-escape в читаемый текст.
    """
    import io

    raw = file_bytes.decode('latin-1', errors='ignore')
    m_cpg = re.search(r'\\ansicpg(\d+)', raw[:2000])
    cp = f"cp{m_cpg.group(1)}" if m_cpg else 'cp1251'

    chars = []
    i = 0
    n = len(raw)
    while i < n:
        c = raw[i]
        if c == '\\':
            if raw[i:i + 2] == '\\u':
                j = i + 2
                num = ''
                while j < n and raw[j].isdigit():
                    num += raw[j]
                    j += 1
                if num:
                    code = int(num)
                    if code > 32767:
                        code -= 65536
                    try:
                        chars.append(chr(code))
                    except Exception:
                        chars.append('?')
                    # пропустить ';' если есть
                    if j < n and raw[j] == ';':
                        j += 1
                    i = j
                    continue
                else:
                    i += 1
                    continue
            else:
                # пропускаем управляющую команду до пробела/неконтрольного символа
                j = i + 1
                while j < n and raw[j] != ' ' and raw[j] != '\\' and raw[j] != '{' and raw[j] != '}':
                    j += 1
                i = j
                continue
        elif c in ('{', '}'):
            i += 1
            continue
        else:
            try:
                chars.append(c.encode('latin-1').decode(cp))
            except Exception:
                chars.append(c)
            i += 1

    txt = "".join(chars)
    section_pattern = re.compile(r'(?m)^(\d+(?:\.\d+)+[а-я]?\.?)\s+(.+)')
    matches = list(section_pattern.finditer(txt))
    if not matches:
        return _fallback_split_by_length(txt)

    sections = []
    for k, m in enumerate(matches):
        label = m.group(1)
        start = m.end()
        end = matches[k + 1].start() if k + 1 < len(matches) else len(txt)
        text = txt[start:end].strip()
        if len(text) > 20:
            sections.extend(_split_long_section(f"п. {label}", text))
    return sections


def compute_checksum(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()
