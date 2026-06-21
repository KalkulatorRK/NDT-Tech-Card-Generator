"""
Представления приложения «Аккаунты».

Регистрация, вход/выход, личный кабинет, редактирование профиля.
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django_ratelimit.decorators import ratelimit

from .forms import RegistrationForm, LoginForm, ProfileEditForm, ResendVerificationForm
from .models import CustomUser, UserBalance
from .email_verification import send_verification_email, verify_email_token, EmailSendError
from techcards.models import TechCard, NormativeDocument


@ratelimit(key='ip', rate='5/h', method='POST', block=False)
def register_view(request):
    """Регистрация нового пользователя."""
    if request.user.is_authenticated:
        return redirect('cabinet')

    if getattr(request, 'limited', False):
        messages.error(
            request,
            'Превышен лимит попыток регистрации с вашего IP-адреса. '
            'Повторите попытку позже.'
        )
        return render(request, 'accounts/register.html', {'form': RegistrationForm()})

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserBalance.objects.create(user=user)
            try:
                send_verification_email(user)
            except EmailSendError as exc:
                messages.warning(
                    request,
                    f'Аккаунт создан, но письмо не удалось отправить: {exc} '
                    'Запросите повторную отправку на странице входа.'
                )
                return redirect('resend_verification')
            messages.success(
                request,
                'Аккаунт создан. Мы отправили письмо с ссылкой для подтверждения '
                f'адреса {user.email}. Проверьте входящие (и папку «Спам»).'
            )
            return redirect('registration_complete')
    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def registration_complete_view(request):
    """Страница после регистрации — ожидание подтверждения email."""
    if request.user.is_authenticated and request.user.email_verified:
        return redirect('cabinet')
    return render(request, 'accounts/registration_complete.html')


@ratelimit(key='ip', rate='10/h', method='POST', block=False)
def resend_verification_view(request):
    """Повторная отправка письма подтверждения email."""
    if request.user.is_authenticated and request.user.email_verified:
        return redirect('cabinet')

    if getattr(request, 'limited', False):
        messages.error(
            request,
            'Превышен лимит запросов. Повторите попытку позже.'
        )
        return render(request, 'accounts/resend_verification.html', {
            'form': ResendVerificationForm(),
        })

    if request.method == 'POST':
        form = ResendVerificationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()
            try:
                user = CustomUser.objects.get(email__iexact=email)
                if user.email_verified:
                    messages.info(request, 'Этот адрес уже подтверждён. Вы можете войти.')
                    return redirect('login')
                send_verification_email(user)
                messages.success(
                    request,
                    f'Письмо с подтверждением отправлено на {email}.'
                )
                return redirect('registration_complete')
            except CustomUser.DoesNotExist:
                messages.success(
                    request,
                    'Если указанный адрес зарегистрирован, письмо будет отправлено.'
                )
                return redirect('registration_complete')
            except EmailSendError as exc:
                messages.error(request, str(exc))
    else:
        form = ResendVerificationForm()

    return render(request, 'accounts/resend_verification.html', {'form': form})


def verify_email_view(request, uidb64, token):
    """Подтверждение email по ссылке из письма."""
    success, user, message = verify_email_token(uidb64, token)
    if success and user:
        messages.success(request, message)
        return redirect('login')
    messages.error(request, message)
    return render(request, 'accounts/verify_email_failed.html', {'message': message})


@ratelimit(key='ip', rate='20/h', method='POST', block=False)
def login_view(request):
    """Вход в систему."""
    if request.user.is_authenticated:
        return redirect('cabinet')

    if getattr(request, 'limited', False):
        messages.error(
            request,
            'Превышен лимит попыток входа. Повторите попытку позже.'
        )
        return render(request, 'accounts/login.html', {'form': LoginForm()})

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next', 'cabinet')
            messages.success(request, f'Вы вошли в систему как {user}.')
            return redirect(next_url)
        elif getattr(form, 'email_not_verified', False):
            messages.warning(
                request,
                'Подтвердите адрес электронной почты. '
                'Проверьте входящие или запросите повторную отправку на странице входа.'
            )
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
