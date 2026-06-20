"""Административная панель форума."""
from django.contrib import admin
from django.utils.html import format_html
from .models import ChatRoom, Message, ChatMembership


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ('author', 'text', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'room_type', 'get_messages_count', 'is_active', 'is_pinned', 'created_at')
    list_filter = ('room_type', 'is_active', 'is_pinned')
    list_editable = ('is_active', 'is_pinned')
    search_fields = ('name', 'description')
    inlines = [MessageInline]

    @admin.display(description='Сообщений')
    def get_messages_count(self, obj):
        return obj.messages.count()

    actions = ['pin_rooms', 'unpin_rooms']

    @admin.action(description='Закрепить выбранные темы')
    def pin_rooms(self, request, queryset):
        queryset.update(is_pinned=True)

    @admin.action(description='Открепить выбранные темы')
    def unpin_rooms(self, request, queryset):
        queryset.update(is_pinned=False)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('pk', 'author', 'room', 'get_text_short', 'created_at')
    list_filter = ('room', 'created_at')
    search_fields = ('text', 'author__username')
    date_hierarchy = 'created_at'

    @admin.display(description='Текст')
    def get_text_short(self, obj):
        return obj.text[:80]
