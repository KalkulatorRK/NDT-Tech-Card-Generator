"""
Тесты приложения «Оценка качества».
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import QualityAssessment, DefectEntry

User = get_user_model()


class QualityViewTests(TestCase):
    """Тесты представлений оценки качества."""

    def setUp(self):
        self.client = Client()

    def test_form_accessible_as_guest(self):
        """Форма оценки доступна гостям."""
        response = self.client.get(reverse('quality_form'))
        self.assertEqual(response.status_code, 200)

    def test_assessment_submission(self):
        """Отправка формы оценки создаёт объект QualityAssessment."""
        self.client.get(reverse('quality_form'))  # Инициализируем сессию
        data = {
            'normative_doc': 'НП-105-18',
            'weld_category': 'II',
            'wall_thickness': '10',
            'weld_length': '500',
            'defect_count': '1',
            'defect_0-defect_type': 'pore',
            'defect_0-size_1': '0.5',
            'defect_0-size_2': '0',
            'defect_0-count': '1',
        }
        response = self.client.post(reverse('quality_form'), data)
        # Должна отображаться страница результата
        self.assertEqual(response.status_code, 200)
        self.assertIn('assessment_data', response.context)

    def test_guest_counter_increments(self):
        """Счётчик гостевых оценок увеличивается после отправки."""
        session = self.client.session
        session['guest_quality_count'] = 0
        session.save()

        data = {
            'normative_doc': 'НП-105-18',
            'weld_category': 'II',
            'wall_thickness': '10',
            'defect_count': '1',
            'defect_0-defect_type': 'pore',
            'defect_0-size_1': '0.5',
            'defect_0-size_2': '0',
            'defect_0-count': '1',
        }
        self.client.post(reverse('quality_form'), data)
        # Проверяем счётчик в сессии
        session = self.client.session
        self.assertEqual(session.get('guest_quality_count', 0), 1)

    def test_guest_blocked_after_limit(self):
        """Гость перенаправляется на регистрацию после исчерпания лимита."""
        session = self.client.session
        session['guest_quality_count'] = 3  # Лимит достигнут
        session.save()

        response = self.client.get(reverse('quality_form'))
        self.assertRedirects(response, reverse('register'))
