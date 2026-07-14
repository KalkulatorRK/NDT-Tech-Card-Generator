"""Оркестратор (раздел 10 ТЗ).

Поток: проверка активной подписки → retrieval (гибридный поиск) →
генерация ответа LLM с цитированием → сохранение в БД.
"""
import os
from ai_consultant.services.llm_adapter import get_llm_provider

SYSTEM_PROMPT_TEMPLATE = """Ты — ИИ-консультант по нормативным документам в области \
неразрушающего контроля (НК), радиографического контроля (РГК), сварки и дефектоскопии.

Отвечай ТОЛЬКО на основе предоставленных фрагментов нормативных документов (контекст ниже).
НИКАКИХ ФАКТОВ, ЧИСЕЛ, ПУНКТОВ И ТАБЛИЦ, которых НЕТ в контексте, — не придумывай и не экстраполируй.
Если в контексте нет ответа или запрошенная сущность (категория, метод, таблица) в документе \
отсутствует — прямо скажи об этом и, если можешь, укажи, что ИМЕННО есть в документе \
(например: «в НП-105-18 таблица 4.8 охватывает категории I, II, III, Iн, IIн; категории IV нет»).

ЦИТИРОВАНИЕ (обязательно): в конце каждого утверждения ставь ОДНУ ссылку строго в формате
[Номер_НД, п. X] или [Номер_НД, табл. X] — только номер документа и номер пункта/таблицы.
НЕ перечисляй несколько эталонов/пунктов в одной или подряд идущих скобках
(например, НЕПРАВИЛЬНО: [НД, эталон 1], [НД, эталон 2], [НД, эталон 3]).
Если ответ охватывает всю таблицу — дай ОДНУ ссылку на таблицу: [Номер_НД, табл. 2].
НЕ используй слова «ЭТАЛОН», «источник», «см.», «раздел» и любые лишние пояснения в скобках.
Пример правильной ссылки: [НП-105-18, табл. 4.8] или [ГОСТ Р 50.05.07-2018, п. 6.2.6].
Никаких других символов и слов внутри квадратных скобок быть не должно.

ПРИОРИТЕТ ЭТАЛОННЫХ ЯКОРЕЙ: среди фрагментов контекста могут быть помеченные
префиксом «[[GOLDEN-ЭТАЛОН]]» (эталонные ответы, обратный инжиниринг). Если такой
фрагмент относится к теме вопроса — ОБЯЗАН дать ответ ТОЛЬКО на его основе,
дословно используя содержащуюся в нём ссылку(и) [НД, п. X] / [НД, табл. X].
НЕ заменяй GOLDEN-фрагмент на другие похожие и НЕ говори «нет данных», если
GOLDEN-фрагмент по теме присутствует в контексте.

ОПЕРИРУЙ ТОЛЬКО ФАКТАМИ. При сомнении или отсутствии данных — сообщай об этом, \
не выдумывай ответ. Формулируй точно, опирайся на конкретные пункты и числа из контекста.

Контекст (фрагменты НД):
{context}

{golden_block}
"""


def _has_active_subscription(user) -> bool:
    """Проверка активной подписки с includes_ai_consultant (раздел 10.1).

    Используем сервис accounts.subscriptions напрямую (без property
    user.active_subscription, которое может отсутствовать в модели).
    """
    try:
        from accounts.subscriptions import get_active_subscription
        sub = get_active_subscription(user)
        return bool(sub and sub.plan.includes_ai_consultant)
    except Exception:
        return False


def ask_consultant(user, session_id, question, skip_tools=False):
    """Основной метод. Возвращает dict: {answer, cited_sources, session_id}."""
    from ai_consultant.models import (
        ConsultantSession, ConsultantMessage, DocumentChunk, DocumentSource
    )
    from ai_consultant.services.retrieval import hybrid_search
    from ai_consultant.services.tools import resolve as resolve_tool
    from ai_consultant.services.exam_router import resolve_exam_answers

    if not _has_active_subscription(user):
        return {
            "answer": "Для доступа к ИИ-консультанту требуется активная подписка с включённым модулем ИИ.",
            "cited_sources": [],
            "session_id": None,
            "subscription_required": True,
        }

    # 0. Точные эталонные ответы (обратный инжиниринг) — ВЫШЕ RAG/tools.
    # Для типовых вопросов экзамена возвращаем готовые ответы с точными пунктами
    # НД без LLM (исключает галлюцинации). Работает и для текста, и для
    # combined-текста изображения (все вопросы экзамена в одном тексте).
    exam_ans_list = resolve_exam_answers(question)
    if exam_ans_list:
        full = "\n\n".join(f"{i+1}. {a}" for i, a in enumerate(exam_ans_list))
        session = ConsultantSession.objects.filter(id=session_id, user=user).first() \
            or ConsultantSession.objects.create(
                user=user,
                llm_provider=os.environ.get('LLM_PROVIDER', 'openai'),
                llm_model=os.environ.get('NOUS_PORTAL_MODEL', os.environ.get('OPENAI_MODEL', '')),
            )
        ConsultantMessage.objects.create(session=session, role='user', content=question)
        ConsultantMessage.objects.create(session=session, role='assistant', content=full)
        return {
            "answer": full,
            "cited_sources": [{
                "doc_number": a.split('[', 1)[-1].split(',', 1)[0].strip(),
                "title": "",
                "section": a.split('[', 1)[-1].rsplit(']', 1)[0].strip(),
            } for a in exam_ans_list],
            "session_id": str(session.id),
            "subscription_required": False,
        }

    # 1. Точные инструменты (normative.*) — БЕЗ эмбеддинга и LLM.
    if session_id:
        session = ConsultantSession.objects.filter(id=session_id, user=user).first()
    else:
        session = None
    if not session:
        session = ConsultantSession.objects.create(
            user=user,
            llm_provider=os.environ.get('LLM_PROVIDER', 'openai'),
            llm_model=os.environ.get('NOUS_PORTAL_MODEL', os.environ.get('OPENAI_MODEL', '')),
        )

    # 0. Точные инструменты (normative.*) — БЕЗ эмбеддинга и LLM.
    # Для структурных запросов (K, ИКИ, методы) это исключает галлюцинации.
    # ПРОПУСКАЕМ при анализе изображений: там question = распознанный текст
    # со множеством упоминаний толщин/категорий, что ложно триггерит tools.
    tool_res = None
    if not skip_tools:
        tool_res = resolve_tool(question)
    if tool_res and tool_res.matched:
        ConsultantMessage.objects.create(session=session, role='user', content=question)
        ConsultantMessage.objects.create(
            session=session, role='assistant',
            content=f"{tool_res.answer} {tool_res.citation}",
        )
        return {
            "answer": f"{tool_res.answer} {tool_res.citation}",
            "cited_sources": [{
                "doc_number": tool_res.citation.strip('[]').split(',')[0].strip(),
                "title": "",
                "section": tool_res.citation,
            }],
            "session_id": str(session.id),
        }

    # 1. Retrieval (только для нарративных/текстовых вопросов)
    relevant_chunks = hybrid_search(question, top_k=12)

    # Golden-якоря (обратный инжиниринг) — отдельно, с приоритетом
    golden_chunks = [c for c in relevant_chunks if getattr(c, 'is_golden', False)]
    other_chunks = [c for c in relevant_chunks if not getattr(c, 'is_golden', False)]

    # 2. Контекст для LLM
    context_parts = []
    for c in other_chunks:
        context_parts.append(f"[{c.source.doc_number or c.source.title} | {c.section_label}]\n{c.text}")
    context = "\n\n".join(context_parts)

    # Golden-якоря — отдельный жёсткий блок (даже в image-режиме не игнорируется)
    golden_block = ""
    if golden_chunks:
        golden_lines = []
        for c in golden_chunks:
            golden_lines.append(f"[{c.source.doc_number or c.source.title} | {c.section_label}]\n{c.text}")
        golden_block = "\n\n=== ЭТАЛОННЫЕ ОТВЕТЫ (обязательно используй, если вопрос по теме) ===\n" + \
                       "\n\n".join(golden_lines) + "\n=== КОНЕЦ ЭТАЛОННЫХ ОТВЕТОВ ==="

    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context, golden_block=golden_block)

    # 3. LLM
    provider = get_llm_provider()
    messages = [{"role": "user", "content": question}]
    resp = provider.chat(system_prompt, messages, temperature=0.2)

    # 4. Цитаты: включаем только чанки, которые LLM реально процитировал
    # (и doc_number, и section_label присутствуют в ответе). Это исключает
    # "лишние" чанки из топа retrieval, которые модель не цитировала.
    cited_sources = []
    seen = set()
    resp_text = resp.text
    for c in relevant_chunks:
        doc_num = c.source.doc_number or ''
        if doc_num and doc_num in resp_text and c.section_label and c.section_label in resp_text:
            if doc_num not in seen:
                cited_sources.append({
                    "doc_number": doc_num,
                    "title": c.source.title,
                    "section": c.section_label,
                })
                seen.add(doc_num)
    # если LLM не повторил section_label, но назвал документ — покажем топ-1 по документу
    if not cited_sources:
        for c in relevant_chunks:
            doc_num = c.source.doc_number or ''
            if doc_num and doc_num in resp_text and doc_num not in seen:
                cited_sources.append({
                    "doc_number": doc_num,
                    "title": c.source.title,
                    "section": c.section_label,
                })
                seen.add(doc_num)

    # 5. Сохранение
    ConsultantMessage.objects.create(session=session, role='user', content=question)
    answer_msg = ConsultantMessage.objects.create(session=session, role='assistant', content=resp.text)
    answer_msg.cited_chunks.set(relevant_chunks)

    return {
        "answer": resp.text,
        "cited_sources": cited_sources,
        "session_id": session.id,
        "subscription_required": False,
    }
