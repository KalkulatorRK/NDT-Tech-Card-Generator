"""
Представления приложения «Аккаунты».

Регистрация, вход/выход, личный кабинет, редактирование профиля.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm

from .forms import RegistrationForm, LoginForm, ProfileEditForm
from .models import CustomUser, UserBalance
from techcards.models import TechCard, NormativeDocument


def register_view(request):
    """Регистрация нового пользователя."""
    if request.user.is_authenticated:
        return redirect('cabinet')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Автоматическое создание баланса
            UserBalance.objects.create(user=user)
            # Сразу выполняем вход
            login(request, user)
            messages.success(
                request,
                f'Добро пожаловать, {user.first_name or user.username}! '
                'Ваш аккаунт успешно создан.'
            )
            return redirect('cabinet')
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """Вход в систему."""
    if request.user.is_authenticated:
        return redirect('cabinet')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next', 'cabinet')
            messages.success(request, f'Вы вошли в систему как {user}.')
            return redirect(next_url)
        else:
            messages.error(request, 'Неверный логин или пароль.')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Выход из системы."""
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'Вы вышли из системы.')
    return redirect('home')


@login_required
def cabinet_view(request):
    """Личный кабинет пользователя."""
    user = request.user

    # Получаем или создаём баланс
    balance, _ = UserBalance.objects.get_or_create(user=user)

    # Список созданных техкарт
    techcards = TechCard.objects.filter(user=user).select_related('normative_doc')

    # Перечень документов с информацией о бесплатных картах
    normative_docs = NormativeDocument.objects.filter(is_active=True)
    docs_status = []
    for doc in normative_docs:
        docs_status.append({
            'doc': doc,
            'free_used': not balance.get_free_status(doc.code),
        })

    context = {
        'user': user,
        'balance': balance,
        'techcards': techcards[:10],     # Последние 10
        'total_techcards': techcards.count(),
        'docs_status': docs_status,
    }
    return render(request, 'accounts/cabinet.html', context)


@login_required
def profile_edit_view(request):
    """Редактирование профиля пользователя."""
    user = request.user

    if request.method == 'POST':
        form = ProfileEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлён.')
            return redirect('cabinet')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = ProfileEditForm(instance=user)

    return render(request, 'accounts/profile_edit.html', {'form': form})


@login_required
def password_change_view(request):
    """Смена пароля пользователя."""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Сохраняем сессию после смены пароля
            update_session_auth_hash(request, user)
            messages.success(request, 'Пароль успешно изменён.')
            return redirect('cabinet')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки.')
    else:
        form = PasswordChangeForm(request.user)

    # Применяем классы Bootstrap к полям
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-control'

    return render(request, 'accounts/password_change.html', {'form': form})
