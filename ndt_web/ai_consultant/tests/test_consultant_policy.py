"""Политика консультанта: НД vs справочники, методика генератора."""

from django.test import SimpleTestCase


class NdSourcesTests(SimpleTestCase):
    databases = []

    def test_textbook_not_citable(self):
        from types import SimpleNamespace
        from ai_consultant.services.nd_sources import (
            is_citable_nd_source,
            is_textbook_source,
        )

        gorb = SimpleNamespace(
            doc_type='other',
            doc_number='Горбачёв В.И. Радиографический контроль сварных соединений (2009)',
            title='Горбачёв',
        )
        gost = SimpleNamespace(
            doc_type='gost',
            doc_number='ГОСТ Р 59023.2-2020',
            title='Сварка',
        )
        np_doc = SimpleNamespace(
            doc_type='np',
            doc_number='НП-105-18',
            title='Нормы',
        )
        self.assertTrue(is_textbook_source(gorb))
        self.assertFalse(is_citable_nd_source(gorb))
        self.assertTrue(is_citable_nd_source(gost))
        self.assertTrue(is_citable_nd_source(np_doc))


class GeneratorMethodologyTests(SimpleTestCase):
    databases = []

    def test_methodology_mentions_boring_and_sk(self):
        from ai_consultant.services.generator_methodology import (
            get_generator_methodology_block,
            question_needs_generator_context,
        )

        block = get_generator_methodology_block()
        self.assertIn('С-23-2', block)
        self.assertIn('S_eff', block)
        self.assertIn('S_K', block)
        self.assertIn('59023.2', block)
        self.assertTrue(
            question_needs_generator_context(
                'особенности при просвечивании с расточкой кромок'
            )
        )

    def test_system_prompt_template_has_required_slots(self):
        from ai_consultant.services.orchestrator import SYSTEM_PROMPT_TEMPLATE
        from ai_consultant.services.generator_methodology import (
            get_generator_methodology_block,
        )

        filled = SYSTEM_PROMPT_TEMPLATE.format(
            user_role_block='ROLE',
            generator_methodology=get_generator_methodology_block(),
            context='ND CTX',
            background_context='BG',
            golden_block='',
        )
        self.assertIn('ТОЛЬКО ОФИЦИАЛЬНЫЕ НД', filled)
        self.assertIn('ЗАПРЕЩЕНО', filled)
        self.assertIn('ВНУТРЕННЯЯ МЕТОДИКА', filled)
        self.assertIn('Условные обозначения', filled)
        self.assertIn('С-23-2', filled)
        self.assertIn('Горбачёва', filled)  # запрет упоминается явно
        self.assertIn('не упоминай генератор', filled.lower())
        cite_rules = filled.split('ЦИТИРОВАНИЕ')[1].split('РАСТОЧКА')[0]
        self.assertIn('Справочно', cite_rules)
        self.assertIn('ЗАПРЕЩЕНО', cite_rules)

    def test_sanitize_strips_generator_mentions(self):
        from ai_consultant.services.orchestrator import _sanitize_consultant_answer

        raw = (
            'По методике генератора «Карта-НК» и нормативной базе РГК, '
            'расточка — по ГОСТ Р 59023.2-2020 (через методику генератора п. 2). '
            'Схемы коды 5a→3а применяются штатно. [Справочно: Горбачёв]'
        )
        clean = _sanitize_consultant_answer(raw)
        self.assertNotIn('методике генератора', clean.lower())
        self.assertNotIn('Справочно', clean)
        self.assertIn('ГОСТ Р 59023.2-2020', clean)
        self.assertIn('3а', clean)
