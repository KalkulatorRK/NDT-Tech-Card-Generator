"""
Models for NDT methods and normative documents.

The actual computational data for each standard is stored in
``ndt_data/<standard_code>.py`` Python modules and referenced by
``NormativeDocument.data_module`` field.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class NDTMethod(models.Model):
    """Non-destructive testing method (e.g. Visual, Radiographic)."""

    class Code(models.TextChoices):
        VISUAL = "VT", _("Визуальный и измерительный (ВИК)")
        RADIOGRAPHIC = "RT", _("Радиографический (РК)")
        CAPILLARY = "PT", _("Капиллярный (ПВК)")
        LEAK = "LT", _("Контроль герметичности (КГ)")
        ULTRASONIC = "UT", _("Ультразвуковой (УЗК)")
        MAGNETIC = "MT", _("Магнитопорошковый (МПД)")

    code = models.CharField(
        max_length=5,
        choices=Code.choices,
        unique=True,
        verbose_name=_("Обозначение метода"),
    )
    name = models.CharField(max_length=200, verbose_name=_("Наименование метода"))
    description = models.TextField(blank=True, verbose_name=_("Описание"))
    is_active = models.BooleanField(default=True, verbose_name=_("Активен"))

    class Meta:
        verbose_name = _("Метод НК")
        verbose_name_plural = _("Методы НК")
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class NormativeDocument(models.Model):
    """
    Normative document (ГОСТ, НП, РД, etc.) used as basis for tech cards.

    ``data_module`` is the dot-path to a Python module inside ``ndt_data/``
    that contains formulas, tables and acceptance criteria for this standard.
    """

    method = models.ForeignKey(
        NDTMethod,
        on_delete=models.PROTECT,
        related_name="documents",
        verbose_name=_("Метод НК"),
    )
    code = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_("Обозначение документа"),
        help_text=_("Например: ГОСТ 7512, ГОСТ Р 50.05.7-2019"),
    )
    name = models.CharField(max_length=500, verbose_name=_("Наименование"))
    short_name = models.CharField(max_length=150, blank=True, verbose_name=_("Краткое наименование"))
    data_module = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_("Модуль данных"),
        help_text=_("Путь к Python-модулю с данными, например: ndt_data.gost_7512"),
    )
    version = models.CharField(max_length=20, blank=True, verbose_name=_("Версия / год"))
    is_active = models.BooleanField(default=True, verbose_name=_("Активен"))
    has_card_template = models.BooleanField(
        default=False,
        verbose_name=_("Есть шаблон техкарты"),
    )
    has_quality_criteria = models.BooleanField(
        default=False,
        verbose_name=_("Есть критерии оценки качества"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Нормативный документ")
        verbose_name_plural = _("Нормативные документы")
        ordering = ["method", "code"]

    def __str__(self):
        return f"{self.code} ({self.method.code})"

    def get_data_module(self):
        """Dynamically import and return the data module for this document."""
        if not self.data_module:
            return None
        import importlib
        try:
            return importlib.import_module(self.data_module)
        except ImportError:
            return None
