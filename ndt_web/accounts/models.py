"""
Модели приложения «Аккаунты».

Содержит расширенную модель пользователя и связанные модели:
баланс операций, история платежей и настройки профиля.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class CustomUser(AbstractUser):
    """
    Расширенная модель пользователя.
    Дополнена полями для профиля специалиста НК и ролями доступа.
    """

    ROLE_ADMIN = 'admin'
    ROLE_USER = 'user'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Администратор'),
        (ROLE_USER, 'Пользователь'),
    ]

    role = models.CharField(
        max_length=10, choices=ROLE_CHOICES, default=ROLE_USER,
        verbose_name='Роль',
    )
    organization = models.CharField(
        max_length=255, blank=True, verbose_name='Организация',
    )
    phone = models.CharField(
        max_length=20, blank=True, verbose_name='Телефон',
    )
    position = models.CharField(
        max_length=255, blank=True, verbose_name='Должность',
    )
    # Квалификационные данные специалиста НК
    ndt_certificate_number = models.CharField(
        max_length=100, blank=True,
        verbose_name='Номер удостоверения НК',
        help_text='Номер квалификационного удостоверения по ГОСТ Р ИСО 9712',
    )
    ndt_level = models.CharField(
        max_length=20, blank=True,
        verbose_name='Уровень квалификации НК',
        help_text='Уровень I, II или III по ГОСТ Р ИСО 9712',
    )
    ndt_methods = models.CharField(
        max_length=200, blank=True,
        verbose_name='Методы НК (в удостоверении)',
    )
    certificate_expiry = models.DateField(
        null=True, blank=True,
        verbose_name='Срок действия удостоверения',
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-date_joined']

    def __str__(self):
        full_name = self.get_full_name()
        return full_name if full_name else self.username

    @property
    def is_admin(self) -> bool:
        """Проверяет, является ли пользователь администратором."""
        return self.role == self.ROLE_ADMIN or self.is_staff

    @property
    def certificate_valid(self) -> bool:
        """Проверяет, действительно ли удостоверение НК на сегодняшний день."""
        if not self.certificate_expiry:
            return False
        return self.certificate_expiry >= timezone.now().date()


class UserBalance(models.Model):
    """
    Баланс операций пользователя.

    Хранит количество оставшихся платных операций и информацию
    о бесплатно использованных операциях по каждому нормативному документу.
    """

    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name='balance',
        verbose_name='Пользователь',
    )
    techcard_credits = models.IntegerField(
        default=0, verbose_name='Оплаченных операций (остаток)',
    )
    # Словарь: {код_нормативного_документа: True/False}
    # True — бесплатная карта уже использована
    free_cards_used = models.JSONField(
        default=dict,
        verbose_name='Использованные бесплатные карты',
        help_text='{"ГОСТ Р 50.05.07-2018": true, ...}',
    )
    total_cards_created = models.IntegerField(
        default=0, verbose_name='Всего карт создано',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Баланс пользователя'
        verbose_name_plural = 'Балансы пользователей'

    def __str__(self):
        return f'Баланс: {self.user} ({self.techcard_credits} опер.)'

    def can_create_techcard(self, normative_doc_code: str) -> tuple[bool, str]:
        """
        Проверяет, может ли пользователь создать новую технологическую карту.

        :param normative_doc_code: код нормативного документа
        :return: (доступно, причина)
        """
        # Первая карта по каждому документу — бесплатно
        if normative_doc_code not in self.free_cards_used:
            return True, 'free'
        # Наличие платных кредитов
        if self.techcard_credits > 0:
            return True, 'paid'
        return False, 'no_credits'

    def use_credit(self, normative_doc_code: str, was_free: bool = False) -> None:
        """
        Расходует одну операцию создания техкарты.

        :param normative_doc_code: код нормативного документа
        :param was_free: была ли операция бесплатной
        """
        if normative_doc_code not in self.free_cards_used:
            # Используем бесплатную
            self.free_cards_used[normative_doc_code] = True
        elif not was_free:
            # Используем платный кредит
            self.techcard_credits = max(0, self.techcard_credits - 1)

        self.total_cards_created += 1
        self.save()

    def add_credits(self, count: int) -> None:
        """
        Пополняет счётчик платных операций.

        :param count: количество добавляемых операций
        """
        self.techcard_credits += count
        self.save()

    def get_free_status(self, normative_doc_code: str) -> bool:
        """Возвращает True, если бесплатная карта по документу ещё не использована."""
        return normative_doc_code not in self.free_cards_used
