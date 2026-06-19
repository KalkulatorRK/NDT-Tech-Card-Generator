"""
Представления приложения «Технологические карты».

Реализует многошаговую форму создания техкарты, личный кабинет
(список и управление картами), скачивание и удаление.
"""

import json
import os

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import timezone

from .models import TechCard, NormativeDocument
from .forms import TechCardStep1Form, TechCardStep2Form, TechCardStep3Form, TechCardConfirmForm
from .generator import generate_tech_card
from accounts.models import UserBalance
from normative.gost_50_05_07 import get_suitable_sources


def home_view(request):
    """Главная страница приложения."""
    normative_docs = NormativeDocument.objects.filter(is_active=True)
    # Последние обновления (для отображения в новостной строке)
    updates = [
        {
            'date': '19.06.2025',
            'text': 'Добавлена поддержка ГОСТ Р 50.05.07-2018 (Радиографический контроль, АЭУ).',
        },
        {
            'date': '01.06.2025',
            'text': 'Запущен раздел «Оценка качества» по НП-105-18.',
        },
        {
            'date': '15.05.2025',
            'text': 'Запуск приложения «НК-Карта» в открытый доступ.',
        },
    ]

    # Счётчик доступных операций для текущего пользователя
    user_balance = None
    if request.user.is_authenticated:
        balance, _ = UserBalance.objects.get_or_create(user=request.user)
        user_balance = balance

    context = {
        'normative_docs': normative_docs,
        'updates': updates,
        'user_balance': user_balance,
    }
    return render(request, 'home.html', context)


@login_required
def cabinet_view(request):
    """Личный кабинет пользователя."""
    user = request.user
    balance, _ = UserBalance.objects.get_or_create(user=user)
    techcards = TechCard.objects.filter(user=user).select_related('normative_doc')
    normative_docs = NormativeDocument.objects.filter(is_active=True)

    docs_status = []
    for doc in normative_docs:
        can_create, reason = balance.can_create_techcard(doc.code)
        docs_status.append({
            'doc': doc,
            'free_used': not balance.get_free_status(doc.code),
            'can_create': can_create,
        })

    context = {
        'balance': balance,
        'techcards': techcards,
        'docs_status': docs_status,
    }
    return render(request, 'accounts/cabinet.html', context)


def method_select_view(request):
    """Страница выбора метода контроля и нормативного документа."""
    normative_docs = NormativeDocument.objects.filter(is_active=True)

    # Группировка по методу контроля
    methods = {}
    for doc in normative_docs:
        method = doc.get_control_method_display()
        if method not in methods:
            methods[method] = []
        methods[method].append(doc)

    return render(request, 'techcards/method_select.html', {'methods': methods})


SESSION_KEY = 'techcard_data'


def _get_session_data(request) -> dict:
    """Получает данные из сессии."""
    return request.session.get(SESSION_KEY, {})


def _save_session_data(request, data: dict):
    """Сохраняет данные в сессию."""
    existing = _get_session_data(request)
    existing.update(data)
    request.session[SESSION_KEY] = existing
    request.session.modified = True


def create_step1_view(request, doc_code):
    """Шаг 1: Идентификационные данные объекта."""
    doc = get_object_or_404(NormativeDocument, code=doc_code, is_active=True)

    if not doc.is_implemented:
        messages.info(request, f'Модуль для «{doc.code}» находится в разработке.')
        return redirect('method_select')

    # Проверка доступности для незарегистрированных
    if not request.user.is_authenticated:
        messages.warning(request, 'Для создания технологической карты необходимо войти в систему.')
        return redirect('login')

    # Проверка баланса
    balance, _ = UserBalance.objects.get_or_create(user=request.user)
    can_create, reason = balance.can_create_techcard(doc.code)
    if not can_create:
        messages.error(
            request,
            'Недостаточно операций для создания технологической карты. '
            'Пожалуйста, пополните баланс в разделе «Оплата».'
        )
        return redirect('tariffs')

    if request.method == 'POST':
        form = TechCardStep1Form(request.POST)
        if form.is_valid():
            _save_session_data(request, {'doc_code': doc_code, **form.cleaned_data})
            return redirect('create_step2', doc_code=doc_code)
    else:
        form = TechCardStep1Form()

    STEP_LABELS = ['Объект', 'Параметры', 'Источник', 'Подтверждение']
    return render(request, 'techcards/create_step1.html', {
        'form': form,
        'doc': doc,
        'step': 1,
        'total_steps': 4,
        'step_labels': STEP_LABELS,
        'free_available': balance.get_free_status(doc.code),
    })


def create_step2_view(request, doc_code):
    """Шаг 2: Материал и геометрия."""
    doc = get_object_or_404(NormativeDocument, code=doc_code)
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        form = TechCardStep2Form(request.POST)
        if form.is_valid():
            _save_session_data(request, form.cleaned_data)
            return redirect('create_step3', doc_code=doc_code)
    else:
        form = TechCardStep2Form()

    STEP_LABELS = ['Объект', 'Параметры', 'Источник', 'Подтверждение']
    return render(request, 'techcards/create_step2.html', {
        'form': form,
        'doc': doc,
        'step': 2,
        'total_steps': 4,
        'step_labels': STEP_LABELS,
    })


def create_step3_view(request, doc_code):
    """Шаг 3: Источник излучения и геометрия просвечивания."""
    doc = get_object_or_404(NormativeDocument, code=doc_code)
    if not request.user.is_authenticated:
        return redirect('login')

    session_data = _get_session_data(request)
    wall_thickness = float(session_data.get('wall_thickness', 10))
    suitable_sources = get_suitable_sources(wall_thickness)

    if request.method == 'POST':
        form = TechCardStep3Form(request.POST)
        if form.is_valid():
            _save_session_data(request, form.cleaned_data)
            return redirect('create_step4', doc_code=doc_code)
    else:
        form = TechCardStep3Form()

    STEP_LABELS = ['Объект', 'Параметры', 'Источник', 'Подтверждение']
    return render(request, 'techcards/create_step3.html', {
        'form': form,
        'doc': doc,
        'step': 3,
        'total_steps': 4,
        'step_labels': STEP_LABELS,
        'suitable_sources': suitable_sources,
        'wall_thickness': wall_thickness,
    })


def create_step4_view(request, doc_code):
    """Шаг 4: Проверка данных и подтверждение."""
    doc = get_object_or_404(NormativeDocument, code=doc_code)
    if not request.user.is_authenticated:
        return redirect('login')

    session_data = _get_session_data(request)

    if request.method == 'POST':
        form = TechCardConfirmForm(request.POST)
        if form.is_valid():
            return redirect('generate_card', doc_code=doc_code)
    else:
        form = TechCardConfirmForm()

    STEP_LABELS = ['Объект', 'Параметры', 'Источник', 'Подтверждение']
    return render(request, 'techcards/create_step4.html', {
        'form': form,
        'doc': doc,
        'step': 4,
        'total_steps': 4,
        'step_labels': STEP_LABELS,
        'session_data': session_data,
    })


@login_required
def generate_card_view(request, doc_code):
    """Генерация технологической карты."""
    doc = get_object_or_404(NormativeDocument, code=doc_code)
    balance, _ = UserBalance.objects.get_or_create(user=request.user)

    can_create, reason = balance.can_create_techcard(doc.code)
    if not can_create:
        messages.error(request, 'Недостаточно операций.')
        return redirect('tariffs')

    input_data = _get_session_data(request)
    if not input_data:
        messages.error(request, 'Данные формы не найдены. Пожалуйста, заполните форму заново.')
        return redirect('create_step1', doc_code=doc_code)

    try:
        # Путь к шаблону DOCX (если загружен в card_templates/)
        template_filename = 'Пример технологической карты радиографического контроля.docx'
        template_path = os.path.join(
            settings.BASE_DIR, 'card_templates', template_filename
        )
        result = generate_tech_card(
            input_data, settings.MEDIA_ROOT,
            template_path=template_path if os.path.exists(template_path) else None,
        )
        was_free = (reason == 'free')

        # Создаём запись в БД
        techcard = TechCard.objects.create(
            user=request.user,
            normative_doc=doc,
            title=input_data.get('object_name', 'Объект контроля'),
            card_number=input_data.get('card_number', ''),
            status=TechCard.STATUS_DONE,
            input_data=input_data,
            generated_data=result.get('params', {}),
            docx_file=result.get('docx_path', ''),
            pdf_file=result.get('pdf_path', ''),
            was_free=was_free,
        )

        # Расходуем кредит
        balance.use_credit(doc.code, was_free=was_free)

        # Очищаем данные из сессии
        if SESSION_KEY in request.session:
            del request.session[SESSION_KEY]
            request.session.modified = True

        messages.success(
            request,
            f'Технологическая карта {techcard.card_number or "#" + str(techcard.pk)} '
            'успешно создана!'
        )

        return redirect('techcard_detail', pk=techcard.pk)

    except Exception as e:
        messages.error(request, f'Ошибка при генерации карты: {str(e)}')
        return redirect('create_step1', doc_code=doc_code)


@login_required
def techcard_list_view(request):
    """Список технологических карт пользователя."""
    techcards = TechCard.objects.filter(user=request.user).select_related('normative_doc')
    return render(request, 'techcards/list.html', {'techcards': techcards})


@login_required
def techcard_detail_view(request, pk):
    """Просмотр конкретной технологической карты."""
    techcard = get_object_or_404(TechCard, pk=pk, user=request.user)
    params = techcard.generated_data

    return render(request, 'techcards/detail.html', {
        'techcard': techcard,
        'params': params,
        'warnings': params.get('warnings', []),
        'errors': params.get('errors', []),
    })


@login_required
def download_file_view(request, pk, file_type):
    """Скачивание файла техкарты (DOCX или PDF)."""
    techcard = get_object_or_404(TechCard, pk=pk, user=request.user)

    if file_type == 'docx' and techcard.docx_file:
        file_path = os.path.join(settings.MEDIA_ROOT, str(techcard.docx_file))
        filename = f'TC_{techcard.card_number or pk}.docx'
    elif file_type == 'pdf' and techcard.pdf_file:
        file_path = os.path.join(settings.MEDIA_ROOT, str(techcard.pdf_file))
        filename = f'TC_{techcard.card_number or pk}.pdf'
    else:
        raise Http404('Файл не найден.')

    if not os.path.exists(file_path):
        raise Http404('Файл не найден на сервере.')

    response = FileResponse(open(file_path, 'rb'))
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_POST
def delete_techcard_view(request, pk):
    """Удаление технологической карты."""
    techcard = get_object_or_404(TechCard, pk=pk, user=request.user)

    # Удаляем файлы
    for file_field in [techcard.docx_file, techcard.pdf_file]:
        if file_field:
            file_path = os.path.join(settings.MEDIA_ROOT, str(file_field))
            if os.path.exists(file_path):
                os.remove(file_path)

    techcard.delete()
    messages.success(request, 'Технологическая карта удалена.')
    return redirect('techcard_list')


def get_sources_ajax(request):
    """AJAX: возвращает подходящие источники для заданной толщины."""
    thickness = request.GET.get('thickness', 10)
    try:
        thickness = float(thickness)
    except (ValueError, TypeError):
        thickness = 10

    sources = get_suitable_sources(thickness)
    return JsonResponse({'sources': sources})
