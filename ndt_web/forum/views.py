"""
Представления форум-чата.
"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db import models as db_models
from django.utils.text import slugify
import uuid

from .models import ChatRoom, Message, ChatMembership
from accounts.models import CustomUser


def _get_or_create_membership(user, room) -> ChatMembership:
    """Возвращает или создаёт участие пользователя в комнате."""
    membership, _ = ChatMembership.objects.get_or_create(user=user, room=room)
    return membership


@login_required
def forum_index(request):
    """
    Главная страница форума.
    Показывает список доступных чатов с количеством непрочитанных.
    """
    user = request.user

    # Публичные темы
    public_rooms = ChatRoom.objects.filter(
        room_type=ChatRoom.TYPE_PUBLIC,
        is_active=True,
    ).order_by('-is_pinned', 'name')

    # Личный чат пользователя с администратором
    private_room = None if user.is_admin else _get_or_create_private_room(user)

    # Для администратора — список ВСЕХ личных чатов пользователей
    admin_private_rooms = []
    if user.is_admin:
        admin_private_rooms_qs = ChatRoom.objects.filter(
            room_type=ChatRoom.TYPE_PRIVATE,
            is_active=True,
        ).order_by('-messages__created_at').distinct()
        for room in admin_private_rooms_qs:
            last_msg = room.last_message
            unread = room.unread_count(user)
            admin_private_rooms.append({
                'room': room,
                'last_message': last_msg,
                'unread': unread,
                'user': room.private_user,
            })

    public_rooms_data = []
    for room in public_rooms:
        last_msg = room.last_message
        unread = room.unread_count(user)
        public_rooms_data.append({
            'room': room,
            'last_message': last_msg,
            'unread': unread,
        })

    private_unread = private_room.unread_count(user) if private_room else 0

    context = {
        'public_rooms': public_rooms_data,
        'private_room': private_room,
        'private_unread': private_unread,
        'admin_private_rooms': admin_private_rooms,
        'active_room': None,
    }
    return render(request, 'forum/index.html', context)


@login_required
def chat_room_view(request, room_id):
    """Страница конкретной комнаты с историей сообщений."""
    user = request.user
    room = get_object_or_404(ChatRoom, pk=room_id, is_active=True)

    # Проверяем доступ к личному чату
    if room.room_type == ChatRoom.TYPE_PRIVATE:
        if room.private_user != user and not user.is_admin:
            messages.error(request, 'У вас нет доступа к этому чату.')
            return redirect('forum_index')

    # Отмечаем сообщения как прочитанные
    membership = _get_or_create_membership(user, room)
    membership.mark_read()

    # Запоминаем последнюю открытую комнату
    request.session['last_chat_room_id'] = room_id

    # История сообщений (последние 100)
    # Используем list() чтобы избежать ошибки при вызове .last() на срезе
    qs = room.messages.select_related('author', 'reply_to__author').order_by('created_at')
    total = qs.count()
    chat_messages = list(qs[max(0, total - 100):])

    last_message_id = chat_messages[-1].pk if chat_messages else 0

    # Данные для сайдбара (те же что на главной)
    public_rooms = ChatRoom.objects.filter(
        room_type=ChatRoom.TYPE_PUBLIC, is_active=True,
    ).order_by('-is_pinned', 'name')

    private_room = None if user.is_admin else _get_or_create_private_room(user)

    admin_private_rooms = []
    if user.is_admin:
        for r in ChatRoom.objects.filter(room_type=ChatRoom.TYPE_PRIVATE, is_active=True).order_by('-id'):
            admin_private_rooms.append({
                'room': r, 'last_message': r.last_message,
                'unread': r.unread_count(user), 'user': r.private_user,
            })

    public_rooms_data = [
        {'room': r, 'last_message': r.last_message, 'unread': r.unread_count(user)}
        for r in public_rooms
    ]

    context = {
        'room': room,
        'chat_messages': chat_messages,
        'public_rooms': public_rooms_data,
        'private_room': private_room,
        'private_unread': private_room.unread_count(user) if private_room else 0,
        'admin_private_rooms': admin_private_rooms,
        'active_room': room,
        'last_message_id': last_message_id,
    }
    return render(request, 'forum/room.html', context)


@login_required
def send_message_view(request, room_id):
    """AJAX: отправка сообщения в комнату."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)

    room = get_object_or_404(ChatRoom, pk=room_id, is_active=True)
    user = request.user

    # Проверка доступа к личному чату
    if room.room_type == ChatRoom.TYPE_PRIVATE:
        if room.private_user != user and not user.is_admin:
            return JsonResponse({'error': 'Нет доступа'}, status=403)

    try:
        body = json.loads(request.body)
        text = body.get('text', '').strip()
        reply_to_id = body.get('reply_to')
    except (json.JSONDecodeError, AttributeError):
        text = request.POST.get('text', '').strip()
        reply_to_id = request.POST.get('reply_to')

    if not text:
        return JsonResponse({'error': 'Текст не может быть пустым'}, status=400)

    if len(text) > 4000:
        return JsonResponse({'error': 'Сообщение слишком длинное (макс. 4000 символов)'}, status=400)

    reply_to = None
    if reply_to_id:
        try:
            reply_to = Message.objects.get(pk=reply_to_id, room=room)
        except Message.DoesNotExist:
            pass

    msg = Message.objects.create(
        room=room,
        author=user,
        text=text,
        reply_to=reply_to,
    )

    # Автоматически обновляем время прочтения для отправителя
    membership = _get_or_create_membership(user, room)
    membership.mark_read()

    return JsonResponse({
        'id': msg.pk,
        'text': msg.text,
        'author': str(msg.author),
        'author_id': msg.author.pk,
        'is_admin': msg.author.is_admin,
        'created_at': msg.created_at.strftime('%H:%M'),
        'created_date': msg.created_at.strftime('%d.%m.%Y'),
        'reply_to': {
            'id': reply_to.pk,
            'author': str(reply_to.author),
            'text': reply_to.text[:60],
        } if reply_to else None,
    })


@login_required
def get_new_messages_view(request, room_id):
    """
    AJAX-поллинг: возвращает новые сообщения начиная с last_id.
    Вызывается клиентом каждые 10 секунд.
    """
    room = get_object_or_404(ChatRoom, pk=room_id)
    user = request.user

    if room.room_type == ChatRoom.TYPE_PRIVATE:
        if room.private_user != user and not user.is_admin:
            return JsonResponse({'error': 'Нет доступа'}, status=403)

    last_id = int(request.GET.get('last_id', 0))

    new_messages = Message.objects.filter(
        room=room, pk__gt=last_id,
    ).select_related('author', 'reply_to__author').order_by('created_at')[:50]

    # Отмечаем как прочитанные
    if new_messages.exists():
        membership = _get_or_create_membership(user, room)
        membership.mark_read()

    data = []
    for msg in new_messages:
        data.append({
            'id': msg.pk,
            'text': msg.text,
            'author': str(msg.author),
            'author_id': msg.author.pk,
            'is_admin': msg.author.is_admin,
            'is_own': msg.author == user,
            'created_at': msg.created_at.strftime('%H:%M'),
            'created_date': msg.created_at.strftime('%d.%m.%Y'),
            'reply_to': {
                'id': msg.reply_to.pk,
                'author': str(msg.reply_to.author),
                'text': msg.reply_to.text[:60],
            } if msg.reply_to else None,
        })

    return JsonResponse({'messages': data})


@login_required
def get_unread_counts_view(request):
    """AJAX: счётчики непрочитанных для всех комнат пользователя."""
    user = request.user
    rooms = ChatRoom.objects.filter(is_active=True)
    data = {
        str(room.pk): room.unread_count(user)
        for room in rooms
    }
    return JsonResponse({'unread': data})


@login_required
def private_chat_view(request):
    """Переход в личный чат пользователя с администратором."""
    room = _get_or_create_private_room(request.user)
    if room:
        return redirect('chat_room', room_id=room.pk)
    return redirect('forum_index')


@login_required
def create_room_view(request):
    """Создание новой публичной темы (только для администраторов)."""
    if not request.user.is_admin:
        messages.error(request, 'Создание тем доступно только администраторам.')
        return redirect('forum_index')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        icon = request.POST.get('icon', 'bi-chat-dots')

        if not name:
            messages.error(request, 'Введите название темы.')
        else:
            slug = slugify(name, allow_unicode=True) + '-' + uuid.uuid4().hex[:6]
            room = ChatRoom.objects.create(
                name=name,
                slug=slug,
                description=description,
                room_type=ChatRoom.TYPE_PUBLIC,
                creator=request.user,
                icon=icon,
            )
            # Приветственное сообщение
            Message.objects.create(
                room=room,
                author=request.user,
                text=f'Тема «{name}» создана. {description}',
            )
            messages.success(request, f'Тема «{name}» создана.')
            return redirect('chat_room', room_id=room.pk)

    return render(request, 'forum/create_room.html', {
        'icons': [
            ('bi-chat-dots', 'Чат'),
            ('bi-question-circle', 'Вопросы'),
            ('bi-tools', 'Техническое'),
            ('bi-book', 'Нормативная база'),
            ('bi-broadcast', 'Объявления'),
            ('bi-people', 'Сообщество'),
            ('bi-lightbulb', 'Предложения'),
            ('bi-bug', 'Сообщить об ошибке'),
        ],
    })


# ------------------------------------------------------------------
# Вспомогательные функции
# ------------------------------------------------------------------

def _get_or_create_private_room(user) -> ChatRoom | None:
    """
    Получает или создаёт личный чат пользователя с администратором.
    Для администратора личного чата нет.
    """
    if user.is_admin:
        return None

    room = ChatRoom.objects.filter(
        room_type=ChatRoom.TYPE_PRIVATE,
        private_user=user,
    ).first()

    if not room:
        room = ChatRoom.objects.create(
            name=f'Чат с администратором — {user}',
            slug=f'private-{user.pk}-{uuid.uuid4().hex[:6]}',
            room_type=ChatRoom.TYPE_PRIVATE,
            private_user=user,
            icon='bi-person-lock',
        )
        # Приветственное сообщение
        Message.objects.create(
            room=room,
            author=user,
            text=(
                'Здравствуйте! Это ваш личный чат с администратором. '
                'Здесь вы можете задать любой вопрос по работе приложения «НК-Карта».'
            ),
        )

    return room
