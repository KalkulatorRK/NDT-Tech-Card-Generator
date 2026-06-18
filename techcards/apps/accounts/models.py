"""
User model with roles and tech-card quota tracking.

Roles:
  - admin: full access via Django admin
  - user: registered user with personal cabinet and paid features
  - guest: anonymous or unregistered visitor (limited access)
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Extended user model with role-based access and payment counter."""

    class Role(models.TextChoices):
        ADMIN = "admin", _("Администратор")
        USER = "user", _("Зарегистрированный пользователь")
        GUEST = "guest", _("Гость")

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USER,
        verbose_name=_("Роль"),
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Телефон"),
    )
    organization = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Организация"),
    )
    # Remaining tech-card generation slots (purchased via payments)
    tech_card_quota = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Доступно разработок техкарт"),
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата регистрации"))

    class Meta:
        verbose_name = _("Пользователь")
        verbose_name_plural = _("Пользователи")

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN or self.is_staff

    @property
    def is_registered_user(self):
        return self.role == self.Role.USER

    def add_quota(self, amount: int) -> None:
        """Increase the tech-card generation counter after payment."""
        self.tech_card_quota = models.F("tech_card_quota") + amount
        self.save(update_fields=["tech_card_quota"])

    def consume_quota(self) -> bool:
        """
        Decrement the quota by 1.

        Returns True if successful, False if quota was already 0.
        """
        if self.tech_card_quota <= 0:
            return False
        self.tech_card_quota = models.F("tech_card_quota") - 1
        self.save(update_fields=["tech_card_quota"])
        return True


class FreeCardUsage(models.Model):
    """
    Tracks which normative documents a user has already used
    for their complimentary first tech-card generation.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="free_card_usages",
        verbose_name=_("Пользователь"),
    )
    normative_doc_code = models.CharField(
        max_length=100,
        verbose_name=_("Код нормативного документа"),
    )
    used_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата использования"))

    class Meta:
        unique_together = ("user", "normative_doc_code")
        verbose_name = _("Бесплатная разработка")
        verbose_name_plural = _("Бесплатные разработки")

    def __str__(self):
        return f"{self.user} — {self.normative_doc_code}"

    @classmethod
    def has_used_free(cls, user, doc_code: str) -> bool:
        return cls.objects.filter(user=user, normative_doc_code=doc_code).exists()
