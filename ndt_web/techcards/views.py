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

    # Счётчик непрочитанных в личном чате с администратором
    private_unread_count = 0
    try:
        from forum.models import ChatRoom
        private_room = ChatRoom.objects.filter(
            room_type=ChatRoom.TYPE_PRIVATE, private_user=user,
        ).first()
        if private_room:
            private_unread_count = private_room.unread_count(user)
    except Exception:
        pass

    # Для администратора: общее количество непрочитанных от пользователей
    admin_unread_total = 0
    if user.is_admin:
        try:
            from forum.models import ChatRoom as CR
            for room in CR.objects.filter(room_type=CR.TYPE_PRIVATE):
                admin_unread_total += room.unread_count(user)
        except Exception:
            pass

    context = {
        'balance': balance,
        'techcards': techcards,
        'docs_status': docs_status,
        'private_unread_count': private_unread_count,
        'admin_unread_total': admin_unread_total,
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
    """Шаг 2: Материал, геометрия и тип сварного соединения."""
    doc = get_object_or_404(NormativeDocument, code=doc_code)
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        form = TechCardStep2Form(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            # Применяем ручной ввод если выбран пункт "другое"
            if not data.get('material') and data.get('material_custom'):
                data['material'] = data['material_custom']
            if not data.get('welding_process') and data.get('welding_process_custom'):
                data['welding_process'] = data['welding_process_custom']
            _save_session_data(request, data)
            return redirect('create_step3', doc_code=doc_code)
    else:
        form = TechCardStep2Form()

    # Данные о типах соединений для JavaScript
    from normative.gost_59023_2 import JOINT_TYPES
    joint_data = {
        code: {
            'name': info['name'],
            'methods': info['methods'],
            'groove': info['groove'],
            'sketch': info.get('sketch', ''),
        }
        for code, info in JOINT_TYPES.items()
    }

    return render(request, 'techcards/create_step2.html', {
        'form': form,
        'doc': doc,
        'step': 2,
        'total_steps': 4,
        'step_labels': ['Объект', 'Параметры', 'Источник', 'Подтверждение'],
        'joint_data_json': json.dumps(joint_data, ensure_ascii=False),
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
            data = form.cleaned_data
            # Применяем ручной ввод плёнки
            if not data.get('film_name') and data.get('film_name_custom'):
                data['film_name'] = data['film_name_custom']
            _save_session_data(request, data)
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

    # Сводка с человекочитаемыми названиями на русском языке
    summary = _build_human_readable_summary(session_data)

    STEP_LABELS = ['Объект', 'Параметры', 'Источник', 'Подтверждение']
    return render(request, 'techcards/create_step4.html', {
        'form': form,
        'doc': doc,
        'step': 4,
        'total_steps': 4,
        'step_labels': STEP_LABELS,
        'summary': summary,
    })


def _build_human_readable_summary(data: dict) -> list:
    """
    Преобразует технические ключи сессионных данных в читаемые
    русскоязычные описания для отображения на шаге 4.

    :param data: словарь из сессии
    :return: список кортежей (заголовок_секции, [(метка, значение), ...])
    """
    from normative.gost_59023_2 import JOINT_TYPES, WELDING_PROCESSES
    from normative.calculations import SCHEME_INFO

    # Словари для перевода кодов
    OBJECT_TYPES = {
        'pipe': 'Трубопровод (кольцевой шов)',
        'flat': 'Плоская деталь / пластина',
        'vessel': 'Сосуд давления / обечайка',
    }
    WELD_CATS = {
        'I': 'I — первый контур АЭУ',
        'II': 'II — вспомогательные системы',
        'III': 'III — прочее оборудование',
        'IV': 'IV — строительные конструкции',
    }
    # Схемы: переводим коды вида '5zh' → 'Чертёж 3ж'
    SCHEME_LABELS = {
        '4_6': 'Чертёж 2 (плоские детали)',
        '5a':  'Чертёж 3а (трубопровод, источник снаружи, 1 стенка)',
        '5b':  'Чертёж 3б (трубопровод, источник снаружи, 1 стенка, эллипс)',
        '5v':  'Чертёж 3в (малый диаметр, источник снаружи, 2 стенки)',
        '5g':  'Чертёж 3г (источник снаружи, 2 стенки)',
        '5d':  'Чертёж 3д (источник снаружи, 2 стенки)',
        '5zh': 'Чертёж 3ж (панорамный, источник на оси)',
        '5z':  'Чертёж 3и (большой диаметр, источник внутри)',
        '5e':  'Чертёж 3е (специальная)',
    }

    # Метки для отдельных полей
    FIELD_LABELS = {
        'organization':       'Организация',
        'object_name':        'Наименование объекта контроля',
        'drawing_number':     'Номер чертежа',
        'weld_number':        'Обозначение сварного соединения',
        'card_number':        'Номер технологической карты',
        'inspector_name':     'Специалист НК (ФИО)',
        'object_type':        'Тип объекта',
        'material':           'Марка стали',
        'wall_thickness':     'Толщина стенки, мм',
        'outer_diameter':     'Наружный диаметр, мм',
        'joint_designation':  'Условное обозначение шва (ГОСТ Р 59023.2-2020)',
        'welding_process':    'Способ сварки',
        'weld_category':      'Категория сварного соединения',
        'source_code':        'Источник излучения',
        'focal_spot_mm':      'Размер фокусного пятна (Φ), мм',
        'source_activity':    'Активность источника',
        'scheme_type':        'Схема просвечивания',
        'film_length_mm':     'Длина плёнки (для схемы 3б), мм',
        'ofd_mm':             'Расстояние объект–детектор (b), мм',
        'film_name':          'Тип радиографической плёнки',
    }

    # Секции для группировки
    sections = [
        ('1. Идентификационные данные', [
            'organization', 'object_name', 'drawing_number',
            'weld_number', 'card_number', 'inspector_name',
        ]),
        ('2. Объект контроля', [
            'object_type', 'material', 'wall_thickness',
            'outer_diameter', 'joint_designation', 'welding_process',
            'weld_category',
        ]),
        ('3. Параметры просвечивания', [
            'source_code', 'focal_spot_mm', 'source_activity',
            'scheme_type', 'film_length_mm', 'ofd_mm', 'film_name',
        ]),
    ]

    def _translate(key, val):
        """Переводит значение поля в читаемый вид."""
        if not val:
            return '—'
        if key == 'object_type':
            return OBJECT_TYPES.get(val, val)
        if key == 'weld_category':
            return WELD_CATS.get(val, val)
        if key == 'scheme_type':
            return SCHEME_LABELS.get(val, val)
        if key == 'welding_process':
            proc = WELDING_PROCESSES.get(str(val), {})
            name = proc.get('name', val)
            return f'Способ {val} — {name}'
        if key == 'joint_designation':
            jt = JOINT_TYPES.get(val, {})
            if jt:
                return f'{val} — {jt.get("name", "")} ({jt.get("groove", "")})'
            return val
        return str(val)

    result = []
    for section_title, keys in sections:
        rows = []
        for key in keys:
            val = data.get(key)
            if val is not None and str(val).strip():
                label = FIELD_LABELS.get(key, key)
                rows.append((label, _translate(key, val)))
        if rows:
            result.append((section_title, rows))
    return result


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


def get_joint_zones_ajax(request):
    """AJAX: рассчитывает зоны контроля для типа соединения и толщины."""
    joint_code = request.GET.get('joint', '')
    thickness = request.GET.get('thickness', 10)
    method = request.GET.get('method', '30')

    try:
        thickness = float(thickness)
    except (ValueError, TypeError):
        thickness = 10.0

    from normative.gost_59023_2 import get_inspection_zone
    result = get_inspection_zone(joint_code, thickness, method)
    return JsonResponse(result)
