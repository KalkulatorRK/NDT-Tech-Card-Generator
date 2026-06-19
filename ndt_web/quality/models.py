"""
Модели приложения «Оценка качества».

Хранит сессии оценки качества сварных соединений
(для зарегистрированных пользователей и гостей).
"""

from django.db import models
from accounts.models import CustomUser


class QualityAssessment(models.Model):
    """
    Сессия оценки качества сварного соединения.

    Привязана к пользователю (если зарегистрирован) или к сессионному
    ключу (для гостей).
    """

    user = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='quality_assessments',
        verbose_name='Пользователь',
    )
    # Для гостей — сессионный ключ
    session_key = models.CharField(
        max_length=40, blank=True,
        verbose_name='Ключ сессии (гость)',
    )
    normative_doc = models.CharField(
        max_length=100, verbose_name='Нормативный документ',
        default='НП-105-18',
    )
    weld_category = models.CharField(
        max_length=10, verbose_name='Категория сварного соединения',
    )
    wall_thickness = models.FloatField(verbose_name='Толщина стенки, мм')
    weld_length = models.FloatField(
        null=True, blank=True, verbose_name='Длина шва, мм',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата')
    verdict = models.CharField(
        max_length=10, blank=True,
        verbose_name='Заключение',
        help_text='ГОДЕН или БРАК',
    )

    class Meta:
        verbose_name = 'Оценка качества'
        verbose_name_plural = 'Оценки качества'
        ordering = ['-created_at']

    def __str__(self):
        owner = self.user or f'Гость ({self.session_key[:8]})'
        return f'Оценка #{self.pk} — {owner} — {self.created_at.strftime("%d.%m.%Y")}'


class DefectEntry(models.Model):
    """Отдельный дефект, введённый пользователем для оценки."""

    DEFECT_TYPE_CHOICES = [
        ('crack', 'Трещина'),
        ('lack_of_fusion', 'Несплавление'),
        ('incomplete_penetration', 'Непровар'),
        ('pore', 'Пора'),
        ('slag', 'Шлаковое включение'),
        ('tungsten', 'Вольфрамовое включение'),
        ('undercut', 'Подрез'),
        ('excess_penetration', 'Превышение проплава'),
        ('surface_defect', 'Поверхностный дефект'),
    ]

    assessment = models.ForeignKey(
        QualityAssessment, on_delete=models.CASCADE, related_name='defects',
        verbose_name='Оценка',
    )
    defect_type = models.CharField(
        max_length=50, choices=DEFECT_TYPE_CHOICES,
        verbose_name='Тип дефекта',
    )
    size_1 = models.FloatField(
        default=0,
        verbose_name='Размер 1 (диаметр/глубина), мм',
    )
    size_2 = models.FloatField(
        default=0,
        verbose_name='Размер 2 (длина/ширина), мм',
    )
    count = models.IntegerField(default=1, verbose_name='Количество')

    class Meta:
        verbose_name = 'Дефект'
        verbose_name_plural = 'Дефекты'

    def __str__(self):
        return f'{self.get_defect_type_display()} ({self.size_1} мм)'


class AssessmentResult(models.Model):
    """Результат оценки конкретного дефекта."""

    assessment = models.ForeignKey(
        QualityAssessment, on_delete=models.CASCADE, related_name='results',
    )
    defect = models.ForeignKey(
        DefectEntry, on_delete=models.CASCADE, related_name='results',
    )
    is_acceptable = models.BooleanField(verbose_name='Допустимо')
    criterion = models.CharField(max_length=500, verbose_name='Критерий приёмки')
    reason = models.TextField(verbose_name='Обоснование')
    reference = models.CharField(max_length=200, verbose_name='Ссылка на пункт НД')
    max_allowed_mm = models.FloatField(default=0, verbose_name='Максимально допустимый размер, мм')

    class Meta:
        verbose_name = 'Результат оценки'
        verbose_name_plural = 'Результаты оценки'
