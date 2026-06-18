from django.contrib import admin
from .models import ChangelogEntry


@admin.register(ChangelogEntry)
class ChangelogEntryAdmin(admin.ModelAdmin):
    list_display = ("title", "is_published", "published_at")
    list_filter = ("is_published",)
    search_fields = ("title", "body")
    list_editable = ("is_published",)
    date_hierarchy = "published_at"
