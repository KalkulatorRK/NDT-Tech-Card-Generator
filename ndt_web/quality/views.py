"""
Представления приложения «Оценка качества».

Обеспечивает форму ввода дефектов, выполнение оценки и вывод результата.
Для незарегистрированных пользователей — счётчик 3 бесплатных оценки.
"""

import os
import uuid

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import FileResponse, Http404
from django.conf import settings

from .forms import QualityAssessmentForm, DefectEntryForm
from .models import QualityAssessment, DefectEntry, AssessmentResult
from .assessor import perform_assessment, generate_assessment_pdf

# Ключ в сессии для подсчёта гостевых оценок
GUEST_COUNTER_KEY = 'guest_quality_count'


def _check_guest_access(request) -> tuple[bool, int]:
    """
    Проверяет доступ гостя к оценке качества.

    :return: (доступ_разрешён, количество_использованных_оценок)
    """
    if request.user.is_authenticated:
        return True, 0
    count = request.session.get(GUEST_COUNTER_KEY, 0)
    limit = getattr(settings, 'GUEST_QUALITY_ASSESSMENTS_LIMIT', 3)
    return count < limit, count


def quality_form_view(request):
    """
    Форма ввода параметров объекта контроля и дефектов.
    """
    allowed, guest_count = _check_guest_access(request)
    guest_limit = getattr(settings, 'GUEST_QUALITY_ASSESSMENTS_LIMIT', 3)

    if not allowed:
        messages.warning(
            request,
            f'Вы использовали {guest_limit} бесплатных оценки. '
            'Для продолжения работы необходимо зарегистрироваться.'
        )
        return redirect('register')

    if request.method == 'POST':
        main_form = QualityAssessmentForm(request.POST)

        # Собираем дефекты из POST-данных (динамически добавляемые строки)
        defect_forms = []
        defect_count = int(request.POST.get('defect_count', 0))
        all_defects_valid = True

        for i in range(defect_count):
            prefix = f'defect_{i}'
            df = DefectEntryForm(request.POST, prefix=prefix)
            if df.is_valid():
                defect_forms.append(df.cleaned_data)
            else:
                all_defects_valid = False

        if main_form.is_valid() and all_defects_valid and defect_forms:
            form_data = main_form.cleaned_data

            # Выполняем оценку
            assessment_result = perform_assessment(form_data, defect_forms)

            # Сохраняем в БД
            assessment_obj = QualityAssessment.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key or '',
                normative_doc=form_data['normative_doc'],
                weld_category=form_data['weld_category'],
                wall_thickness=form_data['wall_thickness'],
                weld_length=form_data.get('weld_length'),
                inclusion_cluster_count_100mm=form_data.get('inclusion_cluster_count_100mm'),
                large_inclusion_count_100mm=form_data.get('large_inclusion_count_100mm'),
                verdict=assessment_result.get('verdict', ''),
            )

            # Сохраняем дефекты и результаты
            defect_objs = []
            for i, d in enumerate(defect_forms):
                defect_obj = DefectEntry.objects.create(
                    assessment=assessment_obj,
                    defect_type=d['defect_type'],
                    size_1=d['size_1'],
                    size_2=d.get('size_2') or 0,
                    count=d.get('count', 1),
                )
                defect_objs.append(defect_obj)

            for i, r in enumerate(assessment_result.get('results', [])):
                if i < len(defect_objs):
                    AssessmentResult.objects.create(
                        assessment=assessment_obj,
                        defect=defect_objs[i],
                        is_acceptable=r.get('is_acceptable', False),
                        criterion=r.get('criterion', ''),
                        reason=r.get('reason', ''),
                        reference=r.get('reference', ''),
                        max_allowed_mm=r.get('max_allowed_mm', 0),
                    )

            # Увеличиваем счётчик гостя
            if not request.user.is_authenticated:
                request.session[GUEST_COUNTER_KEY] = guest_count + 1
                request.session.modified = True

            return render(request, 'quality/result.html', {
                'assessment': assessment_obj,
                'assessment_data': assessment_result,
                'defects_data': defect_forms,
                'is_guest': not request.user.is_authenticated,
                'guest_remaining': max(0, guest_limit - guest_count - 1),
            })
        else:
            if not defect_forms:
                messages.error(request, 'Добавьте хотя бы один дефект для оценки.')
    else:
        main_form = QualityAssessmentForm()

    # Создаём пустую форму для первого дефекта
    initial_defect_form = DefectEntryForm(prefix='defect_0')

    return render(request, 'quality/form.html', {
        'form': main_form,
        'initial_defect_form': initial_defect_form,
        'is_guest': not request.user.is_authenticated,
        'guest_count': guest_count,
        'guest_limit': guest_limit,
        'guest_remaining': max(0, guest_limit - guest_count),
    })


def download_assessment_pdf_view(request, pk):
    """Скачивание PDF результата оценки качества."""
    try:
        if request.user.is_authenticated:
            assessment = QualityAssessment.objects.get(pk=pk, user=request.user)
        else:
            assessment = QualityAssessment.objects.get(
                pk=pk, session_key=request.session.session_key or '',
            )
    except QualityAssessment.DoesNotExist:
        raise Http404('Оценка не найдена.')

    # Получаем дефекты и результаты
    defects = list(assessment.defects.all())
    results = list(assessment.results.all())

    defects_data = [{
        'defect_type': d.defect_type,
        'size_1': d.size_1,
        'size_2': d.size_2,
        'count': d.count,
    } for d in defects]

    results_data = []
    for d, r in zip(defects, results):
        from normative.gost_7512 import format_gost_7512_defect_notation
        gost_notation = format_gost_7512_defect_notation(
            d.defect_type, d.size_1, d.size_2, d.count,
            morphology='cluster' if d.defect_type == 'cluster' else 'single',
            elongated=d.defect_type in ('pore', 'slag', 'tungsten') and d.size_2 > 0,
        )
        results_data.append({
            'defect_name': d.get_defect_type_display(),
            'is_acceptable': r.is_acceptable,
            'criterion': r.criterion,
            'reason': r.reason,
            'reference': r.reference,
            'max_allowed_mm': r.max_allowed_mm,
            'gost_notation': gost_notation,
        })

    from normative.gost_7512 import format_gost_7512_notation_list
    assessment_data = {
        'normative_doc': assessment.normative_doc,
        'weld_category': assessment.weld_category,
        'wall_thickness': assessment.wall_thickness,
        'weld_length': assessment.weld_length,
        'is_acceptable': assessment.verdict == 'ГОДЕН',
        'verdict': assessment.verdict,
        'results': results_data,
        'combined_gost_notation': format_gost_7512_notation_list(
            [item['gost_notation'] for item in results_data],
        ),
    }

    # Генерируем PDF
    uid = uuid.uuid4().hex[:8]
    pdf_path = os.path.join(
        settings.MEDIA_ROOT, f'quality_reports/QA_{assessment.pk}_{uid}.pdf'
    )
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    try:
        generate_assessment_pdf(assessment_data, defects_data, pdf_path)
    except Exception as e:
        messages.error(request, f'Ошибка генерации PDF: {e}')
        return redirect('quality_form')

    response = FileResponse(open(pdf_path, 'rb'))
    response['Content-Disposition'] = f'attachment; filename="QA_{assessment.pk}.pdf"'
    return response
