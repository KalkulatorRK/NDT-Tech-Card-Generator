"""
Настройки административной панели для «Технологических карт».
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import NormativeDocument, TechCard


@admin.register(NormativeDocument)
class NormativeDocumentAdmin(admin.ModelAdmin):
    """Администрирование нормативных документов."""

    list_display = ('code', 'document_kind', 'control_method', 'is_implemented', 'is_active', 'sort_order')
    list_filter = ('document_kind', 'control_method', 'is_implemented', 'is_active')
    search_fields = ('code', 'full_name')
    list_editable = ('is_implemented', 'is_active', 'sort_order')
    ordering = ('sort_order', 'code')


@admin.register(TechCard)
class TechCardAdmin(admin.ModelAdmin):
    """Администрирование технологических карт."""

    list_display = (
        'pk', 'card_number', 'user', 'normative_doc',
        'title', 'status', 'was_free', 'created_at',
        'get_files',
    )
    list_filter = ('status', 'was_free', 'normative_doc', 'created_at')
    search_fields = ('card_number', 'user__username', 'title')
    readonly_fields = ('created_at', 'updated_at', 'input_data', 'generated_data')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    @admin.display(description='Файлы')
    def get_files(self, obj):
        """Ссылки на файлы карты."""
        links = []
        if obj.docx_file:
            links.append(f'<a href="/media/{obj.docx_file}" target="_blank">DOCX</a>')
        if obj.pdf_file:
            links.append(f'<a href="/media/{obj.pdf_file}" target="_blank">PDF</a>')
        return format_html(' | '.join(links)) if links else '—'
