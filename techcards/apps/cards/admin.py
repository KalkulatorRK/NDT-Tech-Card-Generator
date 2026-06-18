from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import TechCard


@admin.register(TechCard)
class TechCardAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "normative_doc", "status", "is_free", "created_at")
    list_filter = ("status", "is_free", "normative_doc__method")
    search_fields = ("title", "user__username", "user__email", "normative_doc__code")
    readonly_fields = ("input_data", "generated_data", "created_at", "updated_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("user", "normative_doc", "title", "status", "is_free")}),
        (_("Данные"), {"fields": ("input_data", "generated_data"), "classes": ("collapse",)}),
        (_("Файлы"), {"fields": ("docx_file", "pdf_file")}),
        (_("Ошибки"), {"fields": ("error_message",)}),
        (_("Даты"), {"fields": ("created_at", "updated_at")}),
    )
