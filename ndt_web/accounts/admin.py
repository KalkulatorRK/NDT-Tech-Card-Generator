"""
Настройки административной панели для приложения «Аккаунты».
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils import timezone

from .models import CustomUser, UserBalance
from .credits import format_credits


class UserBalanceInline(admin.StackedInline):
    """Встроенный блок баланса на странице пользователя."""
    model = UserBalance
    can_delete = False
    verbose_name = 'Баланс кредитов'
    verbose_name_plural = 'Баланс кредитов'
    readonly_fields = ('total_cards_created', 'updated_at')
    fields = ('techcard_credits', 'free_cards_used', 'total_cards_created', 'updated_at')


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Административная страница пользователя."""

    inlines = [UserBalanceInline]
    readonly_fields = ('forum_blocked_at',)
    list_display = (
        'username', 'get_full_name', 'email', 'email_verified', 'organization',
        'role', 'get_credits', 'forum_blocked', 'get_certificate_status',
        'date_joined', 'is_active',
    )
    list_filter = ('role', 'is_active', 'is_staff', 'email_verified', 'forum_blocked', 'ndt_level')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'organization')
    ordering = ('-date_joined',)

    fieldsets = UserAdmin.fieldsets + (
        ('Профессиональные данные', {
            'fields': (
                'role', 'organization', 'phone', 'position',
                'ndt_certificate_number', 'ndt_level', 'ndt_methods',
                'certificate_expiry',
            ),
        }),
        ('Форум', {
            'fields': ('forum_blocked', 'forum_blocked_reason', 'forum_blocked_at'),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Дополнительные данные', {
            'fields': ('email', 'first_name', 'last_name', 'organization', 'role'),
        }),
    )

    @admin.display(description='Кредиты', ordering='balance__techcard_credits')
    def get_credits(self, obj):
        """Отображает количество оставшихся кредитов."""
        try:
            return obj.balance.techcard_credits
        except UserBalance.DoesNotExist:
            return '—'

    @admin.display(description='Удостоверение НК')
    def get_certificate_status(self, obj):
        """Отображает статус удостоверения НК."""
        if not obj.certificate_expiry:
            return format_html('<span style="color: gray;">Не указано</span>')
        if obj.certificate_expiry < timezone.now().date():
            return format_html('<span style="color: red;">Истекло {}</span>', obj.certificate_expiry)
        return format_html('<span style="color: green;">Действует до {}</span>', obj.certificate_expiry)

    actions = ['block_forum', 'unblock_forum']

    @admin.action(description='Заблокировать в форуме')
    def block_forum(self, request, queryset):
        updated = queryset.filter(is_staff=False, role=CustomUser.ROLE_USER).update(
            forum_blocked=True,
            forum_blocked_at=timezone.now(),
        )
        self.message_user(request, f'Заблокировано в форуме: {updated} пользователей.')

    @admin.action(description='Разблокировать в форуме')
    def unblock_forum(self, request, queryset):
        updated = queryset.update(
            forum_blocked=False,
            forum_blocked_reason='',
            forum_blocked_at=None,
        )
        self.message_user(request, f'Разблокировано в форуме: {updated} пользователей.')


@admin.register(UserBalance)
class UserBalanceAdmin(admin.ModelAdmin):
    """Административная страница балансов."""

    list_display = ('user', 'techcard_credits', 'total_cards_created', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('total_cards_created', 'updated_at')

    actions = ['add_10_credits', 'add_5_credits']

    @admin.action(description='Добавить 10 кредитов')
    def add_10_credits(self, request, queryset):
        for balance in queryset:
            balance.add_credits(10)
        self.message_user(request, f'Добавлено 10 кредитов для {queryset.count()} пользователей.')

    @admin.action(description='Добавить 5 кредитов')
    def add_5_credits(self, request, queryset):
        for balance in queryset:
            balance.add_credits(5)
        self.message_user(request, f'Добавлено 5 кредитов для {queryset.count()} пользователей.')
