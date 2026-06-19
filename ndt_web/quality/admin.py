"""Административная панель для «Оценки качества»."""

from django.contrib import admin
from .models import QualityAssessment, DefectEntry, AssessmentResult


class DefectEntryInline(admin.TabularInline):
    model = DefectEntry
    extra = 0
    readonly_fields = ('defect_type', 'size_1', 'size_2', 'count')


class AssessmentResultInline(admin.TabularInline):
    model = AssessmentResult
    extra = 0
    readonly_fields = ('defect', 'is_acceptable', 'criterion', 'reason', 'reference')


@admin.register(QualityAssessment)
class QualityAssessmentAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'normative_doc', 'weld_category', 'wall_thickness', 'verdict', 'created_at')
    list_filter = ('weld_category', 'verdict', 'normative_doc', 'created_at')
    inlines = [DefectEntryInline, AssessmentResultInline]
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
