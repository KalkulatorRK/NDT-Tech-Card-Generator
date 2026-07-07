"""
Представления приложения «Технологические карты».

Реализует многошаговую форму создания техкарты, личный кабинет
(список и управление картами), скачивание и удаление.
"""

import json
import os
from datetime import date, datetime
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import timezone

from .models import TechCard, NormativeDocument
from .forms import TechCardStep1Form, TechCardStep2Form, TechCardStep3Form, TechCardConfirmForm
from .generator import (
    generate_tech_card,
    regenerate_techcard_files,
    get_default_template_path,
    RadiographicTechCardCalculator,
)
from .calculation_reference import generate_calculation_reference_docx
from .scheme_display import get_scheme_user_label, get_scheme_ui_data, SCHEME_CHOICES, get_schemes_for_object_type
from accounts.models import UserBalance
from normative.calculations import resolve_table_b_thickness_mm
from normative.gost_50_05_07 import get_suitable_sources, get_table_b_selection_info, get_suitable_films
from normative.gost_59023_2 import resolve_material_type, get_material_display_name


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
            'text': 'Запуск приложения «Карта-НК» в открытый доступ.',
        },
    ]

    # Счётчик доступных кредитов для текущего пользователя
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


def build_step3_scheme_data(
    wall_thickness: float,
    material_type: str,
    joint_designation: str = '',
    welding_process: str = '30',
    object_type: str = 'pipe',
) -> dict:
    """
    Предрасчёт радиационной толщины, источников и плёнок для каждой схемы.

    Данные встраиваются в шаг 3, чтобы выбор источника работал без AJAX.
    """
    radiation_by_scheme = {}
    sources_by_scheme = {}
    films_by_scheme = {}

    allowed_schemes = get_schemes_for_object_type(object_type)

    for code, _label in SCHEME_CHOICES:
        if not code or code not in allowed_schemes:
            continue
        rad = resolve_table_b_thickness_mm(
            wall_thickness, code, joint_designation, welding_process,
        )
        table_b_thickness = rad['table_b_thickness_mm']
        table_info = get_table_b_selection_info(table_b_thickness, material_type)
        sources = get_suitable_sources(table_b_thickness, material_type)

        radiation_by_scheme[code] = {
            'radiation_thickness_mm': table_b_thickness,
            'wall_desc': rad.get('wall_desc', ''),
            'formula_f': rad.get('formula_f', ''),
            'table_ref': table_info.get('table_ref'),
            'range_label': table_info.get('range_label'),
        }
        sources_by_scheme[code] = sources
        films_by_scheme[code] = {
            src['code']: get_suitable_films(table_b_thickness, material_type, src['code'])
            for src in sources
        }

    return {
        'radiation_by_scheme': radiation_by_scheme,
        'sources_by_scheme': sources_by_scheme,
        'films_by_scheme': films_by_scheme,
    }


def _session_safe_value(value):
    """Приводит значения к типам, совместимым с JSON-сериализацией сессии Django."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _session_safe_data(data: dict) -> dict:
    return {key: _session_safe_value(val) for key, val in data.items()}


def _get_session_data(request) -> dict:
    """Получает данные из сессии."""
    return request.session.get(SESSION_KEY, {})


def _save_session_data(request, data: dict):
    """Сохраняет данные в сессию."""
    existing = _get_session_data(request)
    existing.update(_session_safe_data(data))
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
            'Недостаточно кредитов для создания технологической карты. '
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


def _step2_form_initial(request) -> dict:
    """Данные сессии для шага 2 с нормализацией материала."""
    initial = dict(_get_session_data(request))
    if not initial.get('material') and initial.get('material_custom'):
        initial['material'] = initial['material_custom']
    return initial


def create_step2_view(request, doc_code):
    """Шаг 2: Материал, геометрия и тип сварного соединения."""
    doc = get_object_or_404(NormativeDocument, code=doc_code)
    if not request.user.is_authenticated:
        return redirect('login')

    if request.method == 'POST':
        form = TechCardStep2Form(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if not data.get('material') and data.get('material_custom'):
                data['material'] = data['material_custom']
            if not data.get('welding_process') and data.get('welding_process_custom'):
                data['welding_process'] = data['welding_process_custom']
            _save_session_data(request, data)
            return redirect('create_step3', doc_code=doc_code)
    else:
        form = TechCardStep2Form(initial=_step2_form_initial(request))

    from normative.gost_59023_2 import (
        JOINT_TYPES, WELDING_PROCESSES, get_joint_image_path,
        iter_joint_codes, get_joint_thickness_ranges,
        get_joint_scoped_applicability, format_joint_choice_label,
        get_joint_applicability_for_display, get_joint_group_labels_for_ui,
        get_joint_applicable_material_classes,
    )
    from normative.np_105_18 import get_weld_category_choices
    joint_data = {}
    for code in iter_joint_codes():
        info = JOINT_TYPES[code]
        joint_data[code] = {
            'name': info['name'],
            'methods': info['methods'],
            'groove': info['groove'],
            'image': get_joint_image_path(code),
            'material': info.get('material', 'perlit'),
            'joint_type': info.get('joint_type', 'butt'),
            'gost_table': info.get('gost_table', ''),
            'bead_mode': info.get('bead_mode', 'equal'),
            'thickness_ranges': get_joint_thickness_ranges(code),
            'material_applicability': get_joint_scoped_applicability(code, info)
            if info.get('material') in ('titanium', 'aluminum')
            else get_joint_applicability_for_display(code, info),
            'choice_label': format_joint_choice_label(code, info),
            'applicability': info.get('applicability') or get_joint_applicability_for_display(code, info),
            'applicable_materials': get_joint_applicable_material_classes(code),
            'gost_tables_all': info.get('gost_tables_all', []),
            'group_key': info.get('group_key', ''),
        }
    welding_labels = {
        code: f'{code} — {info["name"]}'
        for code, info in WELDING_PROCESSES.items()
    }

    return render(request, 'techcards/create_step2.html', {
        'form': form,
        'doc': doc,
        'step': 2,
        'total_steps': 4,
        'step_labels': ['Объект', 'Параметры', 'Источник', 'Подтверждение'],
        'joint_data_json': json.dumps(joint_data, ensure_ascii=False),
        'joint_codes_ordered_json': json.dumps(list(joint_data.keys()), ensure_ascii=False),
        'joint_group_labels_json': json.dumps(
            get_joint_group_labels_for_ui(), ensure_ascii=False,
        ),
        'welding_labels_json': json.dumps(welding_labels, ensure_ascii=False),
        'weld_category_choices_json': json.dumps({
            'steel': get_weld_category_choices('steel'),
            'aluminum': get_weld_category_choices('aluminum'),
            'titanium': get_weld_category_choices('titanium'),
        }, ensure_ascii=False),
    })


def create_step3_view(request, doc_code):
    """Шаг 3: Источник излучения и геометрия просвечивания."""
    doc = get_object_or_404(NormativeDocument, code=doc_code)
    if not request.user.is_authenticated:
        return redirect('login')

    session_data = _get_session_data(request)
    wall_thickness = float(session_data.get('wall_thickness', 10))
    material_type = resolve_material_type(session_data.get('material', ''))
    joint_designation = session_data.get('joint_designation', '')
    welding_process = session_data.get('welding_process', '30')
    material_display = get_material_display_name(
        session_data.get('material', ''),
        session_data.get('material_custom', ''),
    )

    object_type = session_data.get('object_type', 'pipe')

    if request.method == 'POST':
        form = TechCardStep3Form(
            request.POST,
            wall_thickness=wall_thickness,
            material_type=material_type,
            joint_designation=joint_designation,
            welding_process=welding_process,
            object_type=object_type,
        )
        if form.is_valid():
            data = form.cleaned_data
            _save_session_data(request, data)
            return redirect('create_step4', doc_code=doc_code)
    else:
        form = TechCardStep3Form(
            wall_thickness=wall_thickness,
            material_type=material_type,
            joint_designation=joint_designation,
            welding_process=welding_process,
            object_type=object_type,
        )

    STEP_LABELS = ['Объект', 'Параметры', 'Источник', 'Подтверждение']
    scheme_data = build_step3_scheme_data(
        wall_thickness, material_type, joint_designation, welding_process,
        object_type=object_type,
    )
    from normative.gost_59023_2 import get_joint_info, WELDING_PROCESSES
    joint_info = get_joint_info(joint_designation) if joint_designation else {}
    welding_label = ''
    if welding_process and welding_process in WELDING_PROCESSES:
        wp = WELDING_PROCESSES[welding_process]
        welding_label = f'{welding_process} — {wp["name"]}'

    return render(request, 'techcards/create_step3.html', {
        'form': form,
        'doc': doc,
        'step': 3,
        'total_steps': 4,
        'step_labels': STEP_LABELS,
        'wall_thickness': wall_thickness,
        'material_display': material_display,
        'material_type': material_type,
        'session_material': session_data.get('material', ''),
        'joint_designation': joint_designation,
        'joint_info': joint_info,
        'welding_process': welding_process,
        'welding_label': welding_label,
        'object_type': object_type,
        'scheme_ui_json': json.dumps(get_scheme_ui_data(), ensure_ascii=False),
        'sources_by_scheme_json': json.dumps(
            scheme_data['sources_by_scheme'], ensure_ascii=False,
        ),
        'radiation_by_scheme_json': json.dumps(
            scheme_data['radiation_by_scheme'], ensure_ascii=False,
        ),
        'films_by_scheme_json': json.dumps(
            scheme_data['films_by_scheme'], ensure_ascii=False,
        ),
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
    }
    SCHEME_LABELS = {
        code: info.get('name', get_scheme_user_label(code))
        for code, info in SCHEME_INFO.items()
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
        'material':           'Материал контролируемого объекта',
        'wall_thickness':     'Толщина стенки, мм',
        'outer_diameter':     'Наружный диаметр, мм',
        'joint_designation':  'Условное обозначение шва (ГОСТ Р 59023.2-2020)',
        'welding_process':    'Способ сварки',
        'weld_category':      'Категория сварного соединения',
        'source_code':        'Источник излучения',
        'focal_spot_mm':      'Размер фокусного пятна (Φ), мм',
        'source_activity':    'Активность источника',
        'scheme_type':        'Схема просвечивания',
        'iqi_side':           'Положение ИКИ (эталона)',
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
            'scheme_type', 'iqi_side', 'ofd_mm', 'film_name',
        ]),
    ]

    def _translate(key, val):
        """Переводит значение поля в читаемый вид."""
        if not val:
            return '—'
        if key == 'material':
            return get_material_display_name(
                val,
                data.get('material_custom', ''),
            )
        if key == 'object_type':
            return OBJECT_TYPES.get(val, val)
        if key == 'weld_category':
            return WELD_CATS.get(val, val)
        if key == 'scheme_type':
            return SCHEME_LABELS.get(val, val)
        if key == 'iqi_side':
            return {
                'source': 'Со стороны источника',
                'film': 'Со стороны плёнки',
            }.get(val, val)
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
        messages.error(request, 'Недостаточно кредитов.')
        return redirect('tariffs')

    input_data = _get_session_data(request)
    if not input_data:
        messages.error(request, 'Данные формы не найдены. Пожалуйста, заполните форму заново.')
        return redirect('create_step1', doc_code=doc_code)

    try:
        # Путь к шаблону DOCX (если загружен в card_templates/)
        template_path = get_default_template_path()
        result = generate_tech_card(
            input_data, settings.MEDIA_ROOT,
            template_path=template_path,
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

    if file_type == 'reference':
        buffer = generate_calculation_reference_docx(
            techcard.input_data,
            techcard.generated_data,
            card_number=techcard.card_number,
            normative_doc_code=techcard.normative_doc.code,
        )
        filename = f'TS_{techcard.card_number or pk}_расчёты.docx'
        return FileResponse(
            buffer,
            as_attachment=True,
            filename=filename,
            content_type=(
                'application/vnd.openxmlformats-officedocument'
                '.wordprocessingml.document'
            ),
        )

    if file_type == 'docx' and (techcard.docx_file or techcard.generated_data):
        filename = f'TC_{techcard.card_number or pk}.docx'
        content_type = (
            'application/vnd.openxmlformats-officedocument'
            '.wordprocessingml.document'
        )
        need_docx = True
        need_pdf = False
        file_rel = str(techcard.docx_file) if techcard.docx_file else ''
    elif file_type == 'pdf' and (techcard.pdf_file or techcard.generated_data):
        filename = f'TC_{techcard.card_number or pk}.pdf'
        content_type = 'application/pdf'
        need_docx = False
        need_pdf = True
        file_rel = str(techcard.pdf_file) if techcard.pdf_file else ''
    else:
        raise Http404('Файл не найден.')

    file_path = os.path.join(settings.MEDIA_ROOT, file_rel) if file_rel else ''

    if not file_path or not os.path.exists(file_path):
        if not techcard.generated_data:
            raise Http404('Файл не найден на сервере.')
        try:
            regenerate_techcard_files(
                techcard,
                str(settings.MEDIA_ROOT),
                get_default_template_path(),
                docx=need_docx,
                pdf=need_pdf,
            )
        except Exception as exc:
            raise Http404(f'Не удалось восстановить файл: {exc}') from exc
        file_rel = str(techcard.docx_file if file_type == 'docx' else techcard.pdf_file)
        file_path = os.path.join(settings.MEDIA_ROOT, file_rel)
        if not os.path.exists(file_path):
            raise Http404('Файл не найден на сервере.')

    return FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=filename,
        content_type=content_type,
    )


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
    """AJAX: подходящие источники по радиационной толщине, схеме и материалу."""
    scheme = (request.GET.get('scheme') or '').strip()
    material = request.GET.get('material', '')
    joint = request.GET.get('joint', '')
    welding_process = request.GET.get('welding_process', '30')
    try:
        wall_thickness = float(request.GET.get('thickness', 10))
    except (ValueError, TypeError):
        wall_thickness = 10.0

    if not scheme:
        return JsonResponse({'sources': [], 'error': 'scheme_required'})

    material_type = resolve_material_type(material)
    rad = resolve_table_b_thickness_mm(
        wall_thickness, scheme, joint, welding_process,
    )
    table_b_thickness = rad['table_b_thickness_mm']
    sources = get_suitable_sources(table_b_thickness, material_type)
    table_b_info = get_table_b_selection_info(table_b_thickness, material_type)
    return JsonResponse({
        'sources': sources,
        'table_ref': table_b_info.get('table_ref'),
        'range_label': table_b_info.get('range_label'),
        'radiation_thickness_mm': table_b_thickness,
        'wall_desc': rad.get('wall_desc', ''),
        'formula_f': rad.get('formula_f', ''),
        'wall_thickness_mm': wall_thickness,
    })


def get_films_ajax(request):
    """AJAX: допустимые плёнки по табл. Б для радиационной толщины, схемы, материала и источника."""
    scheme = (request.GET.get('scheme') or '').strip()
    material = request.GET.get('material', '')
    joint = request.GET.get('joint', '')
    welding_process = request.GET.get('welding_process', '30')
    source_code = request.GET.get('source', '') or None
    try:
        wall_thickness = float(request.GET.get('thickness', 10))
    except (ValueError, TypeError):
        wall_thickness = 10.0

    material_type = resolve_material_type(material)
    if scheme:
        rad = resolve_table_b_thickness_mm(
            wall_thickness, scheme, joint, welding_process,
        )
        table_b_thickness = rad['table_b_thickness_mm']
    else:
        table_b_thickness = wall_thickness

    films = get_suitable_films(table_b_thickness, material_type, source_code)
    return JsonResponse({
        'films': [{'code': f, 'name': f} for f in films],
        'table_ref': get_table_b_selection_info(table_b_thickness, material_type).get('table_ref'),
        'radiation_thickness_mm': table_b_thickness,
    })


def get_joint_zones_ajax(request):
    """AJAX: рассчитывает зоны контроля для типа соединения и толщины."""
    joint_code = request.GET.get('joint', '')
    thickness = request.GET.get('thickness', 10)
    method = request.GET.get('method', '30')
    reinforcement_removed = request.GET.get('reinforcement_removed', '0') in ('1', 'true', 'on')
    has_backing_ring = request.GET.get('has_backing_ring', '0') in ('1', 'true', 'on')
    backing_raw = request.GET.get('backing_ring_thickness_mm', '')
    material = request.GET.get('material', '')

    try:
        thickness = float(thickness)
    except (ValueError, TypeError):
        thickness = 10.0

    backing_thickness = None
    try:
        if backing_raw:
            backing_thickness = float(backing_raw)
    except (ValueError, TypeError):
        backing_thickness = None

    from normative.gost_59023_2 import get_inspection_zone, resolve_material_type
    result = get_inspection_zone(
        joint_code, thickness, method,
        material_type=resolve_material_type(material),
        material=material,
        reinforcement_removed=reinforcement_removed,
        has_backing_ring=has_backing_ring,
        backing_ring_thickness_mm=backing_thickness,
    )
    return JsonResponse(result)


def build_scheme_preview_context(request) -> dict:
    """
    Собирает данные для предпросмотра расчётов на шаге 3.

    Объединяет сессионные данные (шаги 1–2) с полями формы шага 3 из GET.
    """
    session_data = _get_session_data(request)
    scheme = (request.GET.get('scheme_type') or '').strip()
    source_code = (request.GET.get('source_code') or '').strip()
    scheme_info = get_scheme_ui_data().get(scheme, {})

    if not scheme:
        return {
            'ready': False,
            'scheme_selected': False,
            'message': 'Выберите схему просвечивания.',
        }

    if not source_code:
        return {
            'ready': False,
            'scheme_selected': True,
            'scheme': scheme,
            'scheme_label': get_scheme_user_label(scheme),
            'scheme_img': scheme_info.get('img', ''),
            'scheme_desc': scheme_info.get('desc', ''),
            'message': 'Выберите источник излучения из рекомендованного списка.',
        }

    input_data = {
        **session_data,
        'scheme_type': scheme,
        'source_code': source_code,
        'focal_spot_mm': request.GET.get('focal_spot_mm') or session_data.get('focal_spot_mm', '2.0'),
        'ofd_mm': request.GET.get('ofd_mm') or session_data.get('ofd_mm', '5'),
        'film_name': request.GET.get('film_name') or session_data.get('film_name', ''),
        'iqi_side': request.GET.get('iqi_side') or session_data.get('iqi_side', 'source'),
    }

    calc = RadiographicTechCardCalculator(input_data)
    params = calc.calculate()

    exposure = params.get('exposure_scheme') or {}
    iqi_side = input_data.get('iqi_side', 'source')
    k_required_mm = params.get('required_sensitivity_norm_mm', params.get('required_sensitivity_mm'))
    iqi_wire_diameter_mm = params.get('iqi_wire_diameter_mm')
    iqi_wire_number = params.get('iqi_wire_number')
    k_display_mm = params.get('sensitivity_k_display_mm', k_required_mm)

    exposure = params.get('exposure_scheme') or {}
    L_mm = params.get('L_calculated_mm')
    if L_mm is None:
        L_mm = exposure.get('L_mm')

    return {
        'ready': True,
        'scheme_selected': True,
        'scheme': scheme,
        'scheme_label': get_scheme_user_label(scheme),
        'scheme_img': scheme_info.get('img', ''),
        'scheme_desc': scheme_info.get('desc', ''),
        'f_mm': params.get('f_calculated_mm'),
        'N': params.get('N_calculated'),
        'N_segments': exposure.get('N_segments') or params.get('N_segments'),
        'L_mm': L_mm,
        'film_size': params.get('film_size_label', ''),
        'ug_mm': params.get('geometric_unsharpness_mm'),
        'ug_ok': params.get('geometric_unsharpness_ok', True),
        'k_mm': k_display_mm,
        'k_required_mm': k_required_mm,
        'k_pct': params.get('required_sensitivity_pct'),
        'iqi_side': iqi_side,
        'iqi_wire_number': iqi_wire_number,
        'iqi_wire_diameter_mm': iqi_wire_diameter_mm,
        'iqi_shifted': iqi_side == 'film',
        'sfd_used_mm': params.get('sfd_used_mm'),
        'source_name': (params.get('selected_source') or {}).get('name', source_code),
        'formula': params.get('scheme_formula', ''),
        'is_empirical': params.get('is_empirical', False),
        'empirical_reason': params.get('empirical_reason', ''),
        'warnings': calc.warnings,
        'errors': calc.errors,
        'exposure': exposure,
    }


@login_required
def get_scheme_preview_ajax(request):
    """HTMX: предпросмотр схемы и расчётных параметров f, N, L, Ug, K."""
    context = build_scheme_preview_context(request)
    return render(request, 'techcards/partials/scheme_preview.html', context)
