from django.contrib import admin
from .models import QualityAssessment


@admin.register(QualityAssessment)
class QualityAssessmentAdmin(admin.ModelAdmin):
    list_display = ("__str__", "normative_doc", "created_at")
    list_filter = ("normative_doc__method",)
    search_fields = ("user__username", "normative_doc__code")
    readonly_fields = ("input_data", "results", "created_at")
    date_hierarchy = "created_at"
