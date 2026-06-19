"""
Модели приложения «Технологические карты».

Хранит нормативные документы, параметры и готовые технологические карты.
"""

from django.db import models
from django.utils import timezone

from accounts.models import CustomUser


class NormativeDocument(models.Model):
    """
    Нормативный документ, по которому разрабатываются техкарты.

    Каждая запись идентифицирует конкретный стандарт или норматив.
    """

    METHOD_RT = 'RT'   # Радиографический
    METHOD_VT = 'VT'   # Визуальный и измерительный
    METHOD_PT = 'PT'   # Капиллярный
    METHOD_LT = 'LT'   # Контроль герметичности
    METHOD_UT = 'UT'   # Ультразвуковой
    METHOD_MT = 'MT'   # Магнитопорошковый

    METHOD_CHOICES = [
        (METHOD_RT, 'Радиографический контроль (РГК)'),
        (METHOD_VT, 'Визуальный и измерительный контроль (ВИК)'),
        (METHOD_PT, 'Капиллярный контроль (КК)'),
        (METHOD_LT, 'Контроль герметичности (КГ)'),
        (METHOD_UT, 'Ультразвуковой контроль (УЗК)'),
        (METHOD_MT, 'Магнитопорошковый контроль (МПД)'),
    ]

    code = models.CharField(
        max_length=100, unique=True,
        verbose_name='Обозначение документа',
        help_text='Например: ГОСТ Р 50.05.07-2018',
    )
    full_name = models.TextField(verbose_name='Полное наименование')
    control_method = models.CharField(
        max_length=5, choices=METHOD_CHOICES,
        verbose_name='Метод контроля',
    )
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    is_implemented = models.BooleanField(
        default=False,
        verbose_name='Реализован (не заглушка)',
        help_text='Если снято — показывается пометка «В разработке»',
    )
    sort_order = models.IntegerField(default=100, verbose_name='Порядок сортировки')
    description = models.TextField(blank=True, verbose_name='Краткое описание')

    class Meta:
        verbose_name = 'Нормативный документ'
        verbose_name_plural = 'Нормативные документы'
        ordering = ['sort_order', 'code']

    def __str__(self):
        return self.code

    def get_method_display_short(self):
        """Короткое обозначение метода контроля."""
        return self.control_method


class TechCard(models.Model):
    """
    Технологическая карта неразрушающего контроля.

    Создаётся пользователем на основе нормативного документа.
    Хранит исходные данные, рассчитанные параметры и файлы.
    """

    STATUS_DRAFT = 'draft'
    STATUS_DONE = 'done'
    STATUS_ERROR = 'error'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Черновик'),
        (STATUS_DONE, 'Готова'),
        (STATUS_ERROR, 'Ошибка генерации'),
    ]

    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='techcards',
        verbose_name='Пользователь',
    )
    normative_doc = models.ForeignKey(
        NormativeDocument, on_delete=models.PROTECT,
        verbose_name='Нормативный документ',
    )
    title = models.CharField(max_length=500, verbose_name='Наименование объекта')
    card_number = models.CharField(
        max_length=50, blank=True, verbose_name='Номер техкарты',
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_DRAFT, verbose_name='Статус',
    )
    # Исходные данные, введённые пользователем
    input_data = models.JSONField(
        default=dict, verbose_name='Исходные данные',
    )
    # Рассчитанные и сгенерированные параметры техкарты
    generated_data = models.JSONField(
        default=dict, verbose_name='Параметры техкарты',
    )
    # Файлы готовой техкарты
    docx_file = models.FileField(
        upload_to='techcards/docx/%Y/%m/',
        null=True, blank=True,
        verbose_name='Файл DOCX',
    )
    pdf_file = models.FileField(
        upload_to='techcards/pdf/%Y/%m/',
        null=True, blank=True,
        verbose_name='Файл PDF',
    )
    was_free = models.BooleanField(
        default=False, verbose_name='Создана бесплатно',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Технологическая карта'
        verbose_name_plural = 'Технологические карты'
        ordering = ['-created_at']

    def __str__(self):
        return f"ТК {self.card_number or self.pk} ({self.user.username})"

    def get_status_badge(self):
        """Возвращает CSS-класс для отображения статуса."""
        badges = {
            self.STATUS_DRAFT: 'secondary',
            self.STATUS_DONE: 'success',
            self.STATUS_ERROR: 'danger',
        }
        return badges.get(self.status, 'secondary')

    @property
    def is_ready(self) -> bool:
        """Карта готова к скачиванию."""
        return self.status == self.STATUS_DONE
