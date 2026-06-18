"""Admin configuration for NDT methods and normative documents."""

from django.contrib import admin

from .models import NDTMethod, NormativeDocument


@admin.register(NDTMethod)
class NDTMethodAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")


@admin.register(NormativeDocument)
class NormativeDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "method",
        "short_name",
        "version",
        "has_card_template",
        "has_quality_criteria",
        "is_active",
    )
    list_filter = ("method", "is_active", "has_card_template", "has_quality_criteria")
    search_fields = ("code", "name", "short_name")
    list_editable = ("is_active", "has_card_template", "has_quality_criteria")
    autocomplete_fields = ("method",)
