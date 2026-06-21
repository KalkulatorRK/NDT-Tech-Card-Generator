"""
Тесты приложения «Аккаунты».

Проверяет модели пользователя, баланс операций и представления
регистрации, входа, личного кабинета.
"""

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail

from .models import CustomUser, UserBalance
from .email_verification import verify_email_token
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

User = get_user_model()


class UserModelTests(TestCase):
    """Тесты модели CustomUser."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Иван',
            last_name='Иванов',
            organization='АО Атомстрой',
        )

    def test_str_representation(self):
        """__str__ возвращает полное имя."""
        self.assertEqual(str(self.user), 'Иван Иванов')

    def test_str_fallback_username(self):
        """Если нет имени — возвращается логин."""
        user = User.objects.create_user(username='noname', password='pass123')
        self.assertEqual(str(user), 'noname')

    def test_default_role(self):
        """Роль по умолчанию — 'user'."""
        self.assertEqual(self.user.role, CustomUser.ROLE_USER)

    def test_admin_role(self):
        """Метод is_admin работает правильно."""
        self.assertFalse(self.user.is_admin)
        self.user.role = CustomUser.ROLE_ADMIN
        self.assertTrue(self.user.is_admin)

    def test_superuser_is_admin(self):
        """Суперпользователь считается администратором."""
        su = User.objects.create_superuser('su', 'su@test.com', 'supass123')
        self.assertTrue(su.is_admin)


class UserBalanceTests(TestCase):
    """Тесты модели UserBalance."""

    def setUp(self):
        self.user = User.objects.create_user('baluser', password='pass123')
        self.balance = UserBalance.objects.create(user=self.user)

    def test_initial_credits_zero(self):
        """Начальный баланс — 0 кредитов."""
        self.assertEqual(self.balance.techcard_credits, 0)

    def test_free_card_available_initially(self):
        """Первая бесплатная карта доступна."""
        can, reason = self.balance.can_create_techcard('ГОСТ Р 50.05.07-2018')
        self.assertTrue(can)
        self.assertEqual(reason, 'free')

    def test_free_card_used_after_create(self):
        """После использования бесплатной карты — нет повторного доступа без кредитов."""
        self.balance.use_credit('ГОСТ Р 50.05.07-2018', was_free=True)
        can, reason = self.balance.can_create_techcard('ГОСТ Р 50.05.07-2018')
        self.assertFalse(can)
        self.assertEqual(reason, 'no_credits')

    def test_paid_credit_allows_create(self):
        """Наличие платных кредитов разрешает создание карты."""
        self.balance.add_credits(3)
        # Потратим бесплатную сначала
        self.balance.use_credit('ГОСТ Р 50.05.07-2018', was_free=True)
        can, reason = self.balance.can_create_techcard('ГОСТ Р 50.05.07-2018')
        self.assertTrue(can)
        self.assertEqual(reason, 'paid')

    def test_credits_decrease_on_use(self):
        """Платный кредит уменьшается при использовании."""
        self.balance.add_credits(5)
        # Используем бесплатную сначала
        self.balance.use_credit('ГОСТ Р 50.05.07-2018', was_free=True)
        # Теперь платная
        self.balance.use_credit('ГОСТ Р 50.05.07-2018', was_free=False)
        self.assertEqual(self.balance.techcard_credits, 4)

    def test_add_credits(self):
        """Метод add_credits пополняет баланс."""
        self.balance.add_credits(10)
        self.assertEqual(self.balance.techcard_credits, 10)

    def test_total_cards_counter(self):
        """Счётчик общего количества карт увеличивается."""
        self.balance.use_credit('ГОСТ Р 50.05.07-2018', was_free=True)
        self.assertEqual(self.balance.total_cards_created, 1)

    def test_multiple_docs_independent_free(self):
        """Бесплатные карты по разным документам независимы."""
        self.balance.use_credit('ГОСТ Р 50.05.07-2018', was_free=True)
        # Для другого документа должна быть доступна бесплатная
        can, reason = self.balance.can_create_techcard('НП-105-18')
        self.assertTrue(can)
        self.assertEqual(reason, 'free')

    def test_get_free_status(self):
        """get_free_status правильно отражает использование."""
        self.assertTrue(self.balance.get_free_status('ГОСТ Р 50.05.07-2018'))
        self.balance.use_credit('ГОСТ Р 50.05.07-2018', was_free=True)
        self.assertFalse(self.balance.get_free_status('ГОСТ Р 50.05.07-2018'))


class AuthViewTests(TestCase):
    """Тесты представлений аутентификации."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='viewuser', email='view@test.com', password='viewpass123',
            email_verified=True,
        )
        UserBalance.objects.create(user=self.user)

    def test_login_page_accessible(self):
        """Страница входа доступна."""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_register_page_accessible(self):
        """Страница регистрации доступна."""
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_successful_login(self):
        """Успешный вход перенаправляет в кабинет."""
        response = self.client.post(reverse('login'), {
            'username': 'viewuser',
            'password': 'viewpass123',
        })
        self.assertRedirects(response, reverse('cabinet'))

    def test_failed_login(self):
        """Неверный пароль — остаёмся на странице входа."""
        response = self.client.post(reverse('login'), {
            'username': 'viewuser',
            'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)

    def test_cabinet_requires_login(self):
        """Кабинет доступен только авторизованным."""
        response = self.client.get(reverse('cabinet'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('cabinet')}")

    def test_cabinet_accessible_for_logged_in(self):
        """Кабинет доступен авторизованному пользователю."""
        self.client.login(username='viewuser', password='viewpass123')
        response = self.client.get(reverse('cabinet'))
        self.assertEqual(response.status_code, 200)

    def test_register_creates_user_and_balance(self):
        """Регистрация создаёт пользователя и баланс, отправляет письмо."""
        with override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            response = self.client.post(reverse('register'), {
                'username': 'newuser',
                'email': 'new@test.com',
                'first_name': 'Новый',
                'last_name': 'Пользователь',
                'organization': '',
                'password1': 'TestPass!123',
                'password2': 'TestPass!123',
                'agree_terms': True,
            })
        self.assertRedirects(response, reverse('registration_complete'))
        self.assertTrue(User.objects.filter(username='newuser').exists())
        new_user = User.objects.get(username='newuser')
        self.assertFalse(new_user.email_verified)
        self.assertTrue(UserBalance.objects.filter(user=new_user).exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('new@test.com', mail.outbox[0].to)

    def test_unverified_user_cannot_login(self):
        """Неподтверждённый email блокирует вход."""
        User.objects.create_user(
            username='unverified', email='unv@test.com', password='TestPass!123',
            email_verified=False,
        )
        response = self.client.post(reverse('login'), {
            'username': 'unverified',
            'password': 'TestPass!123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_email_verification_flow(self):
        """Ссылка подтверждения активирует аккаунт."""
        user = User.objects.create_user(
            username='verifyme', email='verify@test.com', password='TestPass!123',
            email_verified=False,
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        response = self.client.get(reverse('verify_email', args=[uid, token]))
        self.assertRedirects(response, reverse('login'))
        user.refresh_from_db()
        self.assertTrue(user.email_verified)
