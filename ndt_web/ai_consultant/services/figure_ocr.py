"""OCR рисунков и таблиц из НД через vision-LLM (OpenAI), а также анализ
изображений, загруженных пользователем в чат консультанта.

Использует OpenAI gpt-4o-mini (или OCR_MODEL из env) для распознавания
текста на рисунках/таблицах и описания схем/дефектограмм.
"""
import os, re, base64, io
from PIL import Image

OCR_MODEL = os.environ.get('OCR_MODEL', 'gpt-4o-mini')

_IMAGE_CACHE = {}


def describe_image(image_bytes: bytes, user_question: str = "") -> str | None:
    """Анализ изображения: OCR + описание схемы/таблицы/дефектограммы."""
    api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('NOUS_PORTAL_API_KEY')
    if not api_key:
        return None
    base_url = os.environ.get('OPENAI_BASE_URL') or os.environ.get('NOUS_PORTAL_BASE_URL', '')
    model = os.environ.get('OCR_MODEL', 'gpt-4o-mini')
    b64 = base64.b64encode(image_bytes).decode('ascii')
    question_part = ""
    if user_question:
        question_part = (
            f"\nВопрос пользователя к этому изображению: «{user_question}». "
            f"Ответь с опорой на нормы НК/РГК (ГОСТ Р 50.05.07, НП-105-18, НП-104-18 и др.)."
        )
    try:
        from openai import OpenAI
        kwargs = {'api_key': api_key}
        if base_url:
            kwargs['base_url'] = base_url
        client = OpenAI(**kwargs)
        resp = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": (
                        "Перед тобой изображение, относящееся к неразрушающему "
                        "контролю (НК), радиографическому контролю (РГК), сварке или "
                        "дефектоскопии. Выполни три шага:\n"
                        "1. ИЗВЛЕКИ ВЕСЬ текст и числа с изображения (подписи, таблицы, "
                        "обозначения позиций, маркировки эталонов/ИКИ, условные знаки).\n"
                        "2. ОПИШИ, что именно нарисовано: тип документа (схема просвечивания, "
                        "дефектограмма, радиографический снимок, таблица чувствительности, "
                        "эталон чувствительности и т.п.), расположение элементов "
                        "(источник излучения, объект, плёнка/кассета, сварной шов).\n"
                        "3. СООТНЕСИ увиденное с нормативной базой: какие пункты/таблицы "
                        "ГОСТ Р 50.05.07-2018, НП-105-18, ГОСТ 7512-82, "
                        "ГОСТ 59023.2-2020 или других НД регламентируют данную схему/"
                        "метод/параметр.\n"
                        "Если на изображении нет ни текста, ни схемы — напиши "
                        "«не удалось распознать» и ничего не выдумывай."
                        f"{question_part}"
                    )},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{b64}",
                        "detail": "auto",
                    }},
                ],
            }],
            max_tokens=2000,
        )
        result = resp.choices[0].message.content.strip()
        if "не удалось распознать" in result.lower():
            return None
        return result
    except Exception as e:
        return None


def _recognize_table(image_bytes: bytes, model: str = OCR_MODEL) -> str:
    """Распознавание таблицы через vision-LLM (схемы, таблицы чувствительности и т.д.)."""
    api_key = os.environ.get('OPENAI_API_KEY') or os.environ.get('NOUS_PORTAL_API_KEY')
    if not api_key:
        return ""
    base_url = os.environ.get('OPENAI_BASE_URL') or os.environ.get('NOUS_PORTAL_BASE_URL', '')
    b64 = base64.b64encode(image_bytes).decode('ascii')
    try:
        from openai import OpenAI
        kwargs = {'api_key': api_key}
        if base_url:
            kwargs['base_url'] = base_url
        client = OpenAI(**kwargs)
        resp = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Извлеки текст из таблицы. Сохрани структуру строк и столбцов. Выведи в виде: Строка 1: колонка1 | колонка2 | ..."},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{b64}",
                        "detail": "auto",
                    }},
                ],
            }],
            max_tokens=2000,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return ""
