"""
Модели форум-чата приложения «НК-Карта».

Структура:
- ChatRoom  — комната (публичная тема или личный чат с администратором)
- Message   — сообщение в комнате
- ChatMembership — участие пользователя в комнате (для отслеживания непрочитанных)
"""

from django.db import models
from django.utils import timezone
from accounts.models import CustomUser


class ChatRoom(models.Model):
    """Комната чата — публичная тема или личный диалог."""

    TYPE_PUBLIC  = 'public'
    TYPE_PRIVATE = 'private'   # Личный чат пользователь ↔ администратор
    TYPE_CHOICES = [
        (TYPE_PUBLIC,  'Публичная тема'),
        (TYPE_PRIVATE, 'Личный чат с администратором'),
    ]

    name        = models.CharField(max_length=200, verbose_name='Название')
    slug        = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True, verbose_name='Описание')
    room_type   = models.CharField(
        max_length=10, choices=TYPE_CHOICES,
        default=TYPE_PUBLIC, verbose_name='Тип',
    )
    # Создатель (None = системная тема, созданная администратором)
    creator = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_rooms',
        verbose_name='Создатель',
    )
    # Для личных чатов: второй участник (пользователь)
    private_user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='private_rooms',
        verbose_name='Пользователь (личный чат)',
    )
    is_active   = models.BooleanField(default=True, verbose_name='Активна')
    is_pinned   = models.BooleanField(default=False, verbose_name='Закреплена')
    created_at  = models.DateTimeField(auto_now_add=True)
    icon        = models.CharField(
        max_length=50, blank=True, default='bi-chat-dots',
        verbose_name='Bootstrap-иконка',
    )

    class Meta:
        verbose_name = 'Комната чата'
        verbose_name_plural = 'Комнаты чата'
        ordering = ['-is_pinned', 'room_type', 'name']

    def __str__(self):
        return self.name

    @property
    def last_message(self):
        """Последнее сообщение в комнате."""
        return self.messages.order_by('-created_at').first()

    def unread_count(self, user) -> int:
        """Количество непрочитанных сообщений для пользователя."""
        membership = self.memberships.filter(user=user).first()
        if not membership:
            return self.messages.exclude(author=user).count()
        return self.messages.filter(
            created_at__gt=membership.last_read_at,
        ).exclude(author=user).count()


class Message(models.Model):
    """Сообщение в комнате чата."""

    room       = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE,
        related_name='messages', verbose_name='Комната',
    )
    author     = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        related_name='forum_messages', verbose_name='Автор',
    )
    text       = models.TextField(verbose_name='Текст сообщения')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited  = models.BooleanField(default=False)
    # Ответ на другое сообщение
    reply_to   = models.ForeignKey(
        'self', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='replies', verbose_name='Ответ на',
    )

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author}: {self.text[:50]}'

    @property
    def is_admin_message(self):
        return self.author.is_admin


class ChatMembership(models.Model):
    """
    Участие пользователя в комнате.
    Хранит дату последнего прочтения для подсчёта непрочитанных.
    """

    user         = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        related_name='chat_memberships',
    )
    room         = models.ForeignKey(
        ChatRoom, on_delete=models.CASCADE,
        related_name='memberships',
    )
    last_read_at = models.DateTimeField(default=timezone.now)
    joined_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'room')
        verbose_name = 'Участие в чате'
        verbose_name_plural = 'Участия в чатах'

    def mark_read(self):
        """Отмечает все сообщения как прочитанные."""
        self.last_read_at = timezone.now()
        self.save(update_fields=['last_read_at'])
