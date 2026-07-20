"""Контекст метода НК для ИИ-консультанта.

Системный подход:
1) Эталонные факты — из normative/gost_50_05_*.py (не зависят от эмбеддингов).
2) RAG по БД — только дополнение внутри профильных НД.
3) Типовые вопросы («что такое ВИК», дефекты) — детерминированно, без LLM.
"""
from __future__ import annotations

import importlib
import re
from typing import Any, Optional

METHOD_PROFILES: dict[str, dict[str, Any]] = {
    'РК': {
        'name': 'радиографический контроль (РГК)',
        'modules': ['gost_50_05_07', 'gost_7512'],
        'doc_prefixes': ['ГОСТ Р 50.05.07', 'ГОСТ 7512', 'НП-105', 'НП-104'],
    },
    'УЗК': {
        'name': 'ультразвуковой контроль',
        'modules': ['gost_50_05_02', 'gost_50_05_04', 'gost_50_05_05'],
        'doc_prefixes': ['ГОСТ Р 50.05.02', 'ГОСТ Р 50.05.04', 'ГОСТ Р 50.05.05'],
    },
    'УЗТ': {
        'name': 'ультразвуковая толщинометрия',
        'modules': ['gost_50_05_03'],
        'doc_prefixes': ['ГОСТ Р 50.05.03'],
    },
    'ВИК': {
        'name': 'визуальный и измерительный контроль',
        'modules': ['gost_50_05_08'],
        'doc_prefixes': ['ГОСТ Р 50.05.08'],
    },
    'КГ': {
        'name': 'контроль герметичности',
        'modules': ['gost_50_05_01'],
        'doc_prefixes': ['ГОСТ Р 50.05.01'],
    },
    'КК': {
        'name': 'капиллярный контроль',
        'modules': ['gost_50_05_09'],
        'doc_prefixes': ['ГОСТ Р 50.05.09'],
    },
    'ПЕРСОНАЛ': {
        'name': 'персонал НК/РК',
        'modules': ['gost_50_05_11'],
        'doc_prefixes': ['ГОСТ Р 50.05.11'],
    },
}

# алиасы в вопросе → код метода
_METHOD_ALIASES: dict[str, str] = {
    'вик': 'ВИК',
    'vt': 'ВИК',
    'визуальн': 'ВИК',
    'измерительн': 'ВИК',
    'рк': 'РК',
    'ргк': 'РК',
    'радиограф': 'РК',
    'узк': 'УЗК',
    'уэск': 'УЗК',
    'ультразвук': 'УЗК',
    'узт': 'УЗТ',
    'толщинометр': 'УЗТ',
    'кг': 'КГ',
    'герметичн': 'КГ',
    'кк': 'КК',
    'капилляр': 'КК',
    'персонал': 'ПЕРСОНАЛ',
}


def _load_module(name: str):
    try:
        return importlib.import_module(f'normative.{name}')
    except Exception:
        return None


def profile_for(scope: Optional[str]) -> Optional[dict]:
    if not scope:
        return None
    return METHOD_PROFILES.get(scope.strip().upper())


def preferred_doc_prefixes(scope: Optional[str]) -> list[str]:
    p = profile_for(scope)
    return list(p['doc_prefixes']) if p else []


def detect_method_from_question(question: str) -> Optional[str]:
    q = (question or '').lower()
    # длинные ключи первыми
    for alias, code in sorted(_METHOD_ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in q:
            return code
    return None


def resolve_effective_scope(question: str, method_scope: Optional[str] = None) -> Optional[str]:
    """Кнопка метода + явное имя метода в вопросе.

    «что такое ВИК» при активном РК → ВИК (не тянуть 50.05.07).
    """
    scope = (method_scope or '').strip().upper() or None
    detected = detect_method_from_question(question)
    q = (question or '').strip().lower()
    if detected and (
        re.search(r'что\s+так|определен|расскажи\s+про|что\s+означает', q)
        or (scope and detected != scope and detected.lower() in q)
    ):
        return detected
    return scope or detected


def _module_intro(M) -> str:
    code = getattr(M, 'DOCUMENT_CODE', '')
    full = getattr(M, 'DOCUMENT_FULL_NAME', code)
    scope = getattr(M, 'SCOPE', '') or getattr(M, 'DOCUMENT_SCOPE', '')
    method = getattr(M, 'METHOD_NAME', '')
    parts = [full]
    if method:
        parts.append(f'Метод: {method}.')
    if scope:
        parts.append(scope)
    return ' '.join(parts)


def canonical_chunks(scope: Optional[str]) -> list[tuple[str, str]]:
    """Эталонные (label, text) из .py модулей профиля."""
    p = profile_for(scope)
    if not p:
        return []
    out: list[tuple[str, str]] = []
    for mod_name in p['modules']:
        M = _load_module(mod_name)
        if not M:
            continue
        code = getattr(M, 'DOCUMENT_CODE', mod_name)
        out.append((f'{code} паспорт', _module_intro(M)))
        fn = getattr(M, 'all_kb_chunks', None)
        if callable(fn):
            try:
                for lbl, txt in fn():
                    if txt and str(txt).strip():
                        out.append((str(lbl), str(txt)))
            except Exception:
                continue
        for attr in (
            'format_sensitivity_table', 'format_ambient_rules', 'format_dm_rules',
            'format_illuminance_rules', 'format_surface_preparation',
            'format_control_sequence', 'format_personnel_rules',
        ):
            f = getattr(M, attr, None)
            if callable(f):
                try:
                    t = f()
                    if t:
                        out.append((f'{code} {attr}', t))
                except Exception:
                    pass
    return out


def select_canonical_context(scope: Optional[str], question: str, max_chars: int = 10000) -> str:
    """Контекст из .py: релевантные вопросу фрагменты + паспорт."""
    chunks = canonical_chunks(scope)
    if not chunks:
        return ''
    q_terms = [t for t in re.split(r'\W+', question.lower()) if len(t) > 2]
    scored: list[tuple[float, str, str]] = []
    for lbl, txt in chunks:
        hay = (lbl + ' ' + txt).lower()
        hit = sum(1 for t in q_terms if t in hay) if q_terms else 0
        bonus = 3.0 if 'паспорт' in lbl.lower() or '§1' in lbl else 0.0
        if any(k in question.lower() for k in ('дефект', 'несплошн', 'трещин', 'выявл')):
            if any(k in hay for k in ('дефект', 'несплошн', 'трещин', 'подрез', 'термин')):
                bonus += 2.0
        scored.append((hit + bonus, lbl, txt))
    scored.sort(key=lambda x: x[0], reverse=True)
    parts = []
    total = 0
    for _, lbl, txt in scored:
        block = f'[{lbl}]\n{txt.strip()}'
        if total + len(block) > max_chars:
            break
        parts.append(block)
        total += len(block) + 2
    return '\n\n'.join(parts)


def _answer_what_is(scope: str) -> Optional[str]:
    p = profile_for(scope)
    if not p:
        return None
    for mod_name in p['modules']:
        M = _load_module(mod_name)
        if not M:
            continue
        code = getattr(M, 'DOCUMENT_CODE', '')
        name = getattr(M, 'METHOD_NAME', p['name'])
        abbr = getattr(M, 'METHOD_CODE', scope)
        scope_txt = getattr(M, 'SCOPE', '') or ''
        # ВИК: термин «визуальный контроль» из TERMS
        terms = getattr(M, 'TERMS', {}) or {}
        term_line = ''
        for entry in terms.values():
            if (entry.get('term') or '').lower() == 'визуальный контроль':
                term_line = f"\n\nПо определению (§3): {entry['definition']}"
                break
        body = scope_txt or p['name']
        return (
            f"**{abbr}** — {name}.\n\n"
            f"По {code}: {body}"
            f"{term_line}"
        )
    return None


def _answer_vik_defects() -> str:
    M = _load_module('gost_50_05_08')
    if not M:
        return ''
    code = M.DOCUMENT_CODE
    terms = getattr(M, 'TERMS', {}) or {}
    defect_bits = []
    for entry in terms.values():
        term = (entry.get('term') or '').lower()
        if any(k in term for k in (
            'трещин', 'подрез', 'непровар', 'наплыв', 'пора', 'кратер',
            'отслоен', 'прожог', 'закат', 'включен', 'вогнутост',
        )):
            defect_bits.append(f"- {entry['term']}: {entry['definition']}")
    checks = getattr(M, 'OPERATIONAL_CONTROL_CHECKS', {}) or {}
    after = checks.get('after_welding') or []
    parts = [
        f'По {code} визуальный контроль направлен на выявление поверхностных '
        f'несплошностей и отклонений формы/геометрии шва (п. 5.1–5.2).',
    ]
    if after:
        parts.append(
            'После сварки, в частности, проверяют: '
            + '; '.join(after[:6])
            + ('…' if len(after) > 6 else '')
            + f' [{code}, п. 5.6].'
        )
    if defect_bits:
        parts.append('Примеры терминов дефектов из §3:\n' + '\n'.join(defect_bits[:12]))
    parts.append(
        f'Нормы оценки качества — по ссылочным ФНП; {code} задаёт методику ВИК, '
        f'а не полную таблицу браковочных норм.'
    )
    return '\n\n'.join(parts)


def try_deterministic_answer(question: str, scope: Optional[str] = None) -> Optional[str]:
    """Ответы без LLM на типовые вопросы по методу НК."""
    q = re.sub(r'\s+', ' ', (question or '').strip().lower())
    if not q:
        return None

    scope_u = (scope or '').strip().upper() or detect_method_from_question(q)

    # «что такое ВИК / УЗК / …» или «что такое визуальный контроль»
    is_what = bool(re.search(
        r'^(что\s+(такое|так+ое|есть|означает)|определени[ея]|расскажи\s+про)\b',
        q,
    )) or bool(re.search(r'\bчто\s+так\w*\b', q))
    if is_what:
        detected = detect_method_from_question(q) or scope_u
        if detected:
            ans = _answer_what_is(detected)
            if ans:
                return ans

    # дефекты / что выявляет ВИК
    if (scope_u == 'ВИК' or detect_method_from_question(q) == 'ВИК') and re.search(
        r'дефект|несплошн|выявля|что\s+ищ', q,
    ):
        ans = _answer_vik_defects()
        if ans:
            return ans

    return None
