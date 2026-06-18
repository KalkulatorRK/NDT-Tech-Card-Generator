"""Admin configuration for user management."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import FreeCardUsage, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "get_full_name", "role", "tech_card_quota", "created_at", "is_active")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name", "organization")
    ordering = ("-created_at",)

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            _("Дополнительно"),
            {
                "fields": ("role", "phone", "organization", "tech_card_quota"),
            },
        ),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            _("Дополнительно"),
            {
                "fields": ("email", "role", "phone", "organization"),
            },
        ),
    )

    actions = ["grant_quota_10"]

    @admin.action(description=_("Начислить 10 разработок"))
    def grant_quota_10(self, request, queryset):
        for user in queryset:
            user.add_quota(10)
        self.message_user(request, _("Начислено 10 разработок выбранным пользователям."))


@admin.register(FreeCardUsage)
class FreeCardUsageAdmin(admin.ModelAdmin):
    list_display = ("user", "normative_doc_code", "used_at")
    search_fields = ("user__username", "normative_doc_code")
    list_filter = ("normative_doc_code",)
