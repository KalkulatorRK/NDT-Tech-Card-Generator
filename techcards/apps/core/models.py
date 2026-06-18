"""
Core models: application news/changelog entries.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class ChangelogEntry(models.Model):
    """News and changelog items shown on the home page."""

    title = models.CharField(max_length=300, verbose_name=_("Заголовок"))
    body = models.TextField(verbose_name=_("Текст"))
    is_published = models.BooleanField(default=True, verbose_name=_("Опубликовано"))
    published_at = models.DateTimeField(verbose_name=_("Дата публикации"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Запись об обновлении")
        verbose_name_plural = _("Обновления и изменения")
        ordering = ["-published_at"]

    def __str__(self):
        return self.title
