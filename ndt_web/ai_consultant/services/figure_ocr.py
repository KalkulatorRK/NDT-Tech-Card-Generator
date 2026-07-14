"""OCR (извлечение текста) из рисунков и таблиц нормативных документов.

ГОСТ/НПА содержат критичную информацию в графике: таблицы (числа, классы
дефектов), формулы, обозначения на схемах просвечивания. Текстовый слой PDF
её не захватывает, поэтому каждую страницу рендерим в изображение и прогоняем
через vision-LLM (тот же провайдер эмбеддингов — OpenAI, единая ось конфигурации).
"""
import base64
import os


def ocr_page_image(image_bytes: bytes, page_label: str) -> str | None:
    """Возвращает извлечённый текст страницы (таблицы, формулы, подписи к рисункам)
    или None, если OCR не дал содержательного результата.
    """
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return None
    model = os.environ.get('OCR_MODEL', 'gpt-4o-mini')
    b64 = base64.b64encode(image_bytes).decode('ascii')
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Это страница нормативного документа (ГОСТ/НПА) с рисунками, "
                                "таблицами и/или формулами. Извлеки ВЕСЬ значимый текст: "
                                "подписи к рисункам, обозначения (например, '1 - источник излучения'), "
                                "содержимое таблиц (сохрани числа и структуру), формулы. "
                                "Если на странице только обычный текст — ничего не добавляй. "
                                "Ответь только извлечёнными данными, без лишних слов."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ],
                }
            ],
            max_tokens=1500,
        )
        text = resp.choices[0].message.content
        if text is None:
            return None
        text = text.strip()
        return text if len(text) > 15 else None
    except Exception as e:
        print(f"[OCR] не удалось обработать {page_label}: {e}")
        return None


def describe_image(image_bytes: bytes, user_question: str = "") -> str | None:
    """Анализ изображения, загруженного пользователем: извлечение текста (OCR) И
    понимание того, что нарисовано (схема, таблица, дефектограмма, плёнка и т.п.),
    и соотнесение с нормативной базой НК/РГК.

    Возвращает компактный текстовый блок для подачи в LLM-консультант, либо None.
    """
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        return None
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
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
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
                                "ГОСТ/НПА этому соответствуют (например, схема 3В — две стенки, "
                                "источник снаружи трубы, просвечивание на эллипс).\n"
                                "Ответь структурированно, без лишних вступлений." + question_part
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    ],
                }
            ],
            max_tokens=1200,
        )
        text = resp.choices[0].message.content
        if text is None:
            return None
        text = text.strip()
        return text if len(text) > 15 else None
    except Exception as e:
        print(f"[OCR] не удалось обработать изображение пользователя: {e}")
        return None
