"""Models for quality assessment sessions."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

GUEST_FREE_ASSESSMENTS = 3


class QualityAssessment(models.Model):
    """Stores input and results for a quality assessment session."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quality_assessments",
        null=True,
        blank=True,
        verbose_name=_("Пользователь"),
    )
    session_key = models.CharField(
        max_length=40,
        blank=True,
        verbose_name=_("Ключ сессии (гость)"),
    )
    normative_doc = models.ForeignKey(
        "standards.NormativeDocument",
        on_delete=models.PROTECT,
        verbose_name=_("Нормативный документ"),
    )
    input_data = models.JSONField(default=dict, verbose_name=_("Исходные данные"))
    results = models.JSONField(default=list, verbose_name=_("Результаты оценки"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата оценки"))

    class Meta:
        verbose_name = _("Оценка качества")
        verbose_name_plural = _("Оценки качества")
        ordering = ["-created_at"]

    def __str__(self):
        owner = str(self.user) if self.user else f"Гость ({self.session_key[:8]})"
        return f"{owner} — {self.normative_doc.code} — {self.created_at:%d.%m.%Y}"


def guest_assessment_count(session_key: str) -> int:
    """Return the number of assessments made by a guest session."""
    return QualityAssessment.objects.filter(
        user__isnull=True, session_key=session_key
    ).count()
