"""
Models for tech card generation requests and resulting files.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


def tech_card_docx_path(instance, filename):
    return f"tech_cards/{instance.user.id}/{instance.id}.docx"


def tech_card_pdf_path(instance, filename):
    return f"tech_cards/{instance.user.id}/{instance.id}.pdf"


class TechCard(models.Model):
    """Represents a generated NDT technology card."""

    class Status(models.TextChoices):
        PENDING = "pending", _("В обработке")
        GENERATED = "generated", _("Сгенерирована")
        ERROR = "error", _("Ошибка")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tech_cards",
        verbose_name=_("Пользователь"),
    )
    normative_doc = models.ForeignKey(
        "standards.NormativeDocument",
        on_delete=models.PROTECT,
        verbose_name=_("Нормативный документ"),
    )
    title = models.CharField(max_length=300, verbose_name=_("Название техкарты"))
    input_data = models.JSONField(default=dict, verbose_name=_("Исходные данные"))
    generated_data = models.JSONField(default=dict, verbose_name=_("Вычисленные данные"))
    docx_file = models.FileField(
        upload_to=tech_card_docx_path,
        blank=True,
        null=True,
        verbose_name=_("Файл DOCX"),
    )
    pdf_file = models.FileField(
        upload_to=tech_card_pdf_path,
        blank=True,
        null=True,
        verbose_name=_("Файл PDF"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name=_("Статус"),
    )
    error_message = models.TextField(blank=True, verbose_name=_("Сообщение об ошибке"))
    is_free = models.BooleanField(default=False, verbose_name=_("Бесплатная разработка"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата изменения"))

    class Meta:
        verbose_name = _("Технологическая карта")
        verbose_name_plural = _("Технологические карты")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.normative_doc.code})"

    def delete(self, *args, **kwargs):
        """Delete associated files when the record is removed."""
        if self.docx_file:
            self.docx_file.delete(save=False)
        if self.pdf_file:
            self.pdf_file.delete(save=False)
        super().delete(*args, **kwargs)
