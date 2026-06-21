"""Тесты форматирования кредитов."""

from django.test import SimpleTestCase

from accounts.credits import credit_word, format_credits


class CreditWordTests(SimpleTestCase):
    def test_singular(self):
        self.assertEqual(credit_word(1), 'кредит')
        self.assertEqual(credit_word(21), 'кредит')

    def test_few(self):
        self.assertEqual(credit_word(2), 'кредита')
        self.assertEqual(credit_word(4), 'кредита')

    def test_many(self):
        self.assertEqual(credit_word(5), 'кредитов')
        self.assertEqual(credit_word(11), 'кредитов')

    def test_format_credits(self):
        self.assertEqual(format_credits(3), '3 кредита')
