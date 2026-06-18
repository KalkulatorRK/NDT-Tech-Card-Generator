"""Views for the quality assessment section."""

import io

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from apps.standards.models import NormativeDocument
from .forms import DefectFormSet, QualityDocumentForm
from .models import QualityAssessment, guest_assessment_count, GUEST_FREE_ASSESSMENTS


def _check_guest_access(request) -> tuple[bool, str]:
    """
    Guests get 3 free assessments, then must register.

    Returns (allowed: bool, message: str).
    """
    if request.user.is_authenticated:
        return True, ""
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key
    count = guest_assessment_count(session_key)
    remaining = GUEST_FREE_ASSESSMENTS - count
    if remaining > 0:
        return True, _(f"Гостевой доступ: осталось {remaining} бесплатных оценок.")
    return False, _("Исчерпан гостевой лимит. Пожалуйста, зарегистрируйтесь для продолжения.")


def quality_home(request):
    """Landing page for quality assessment — choose document."""
    form = QualityDocumentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        doc = form.cleaned_data["normative_doc"]
        return redirect("quality:assess", doc_id=doc.pk)
    return render(request, "quality/quality_home.html", {"form": form})


def quality_assess(request, doc_id):
    """Enter defect data and get assessment results."""
    doc = get_object_or_404(NormativeDocument, pk=doc_id, is_active=True, has_quality_criteria=True)
    data_module = doc.get_data_module()

    if data_module is None:
        messages.error(request, _("Данные критериев для выбранного документа недоступны."))
        return redirect("quality:home")

    allowed, access_msg = _check_guest_access(request)
    if not allowed:
        messages.warning(request, access_msg)
        return redirect("account_login")

    # Get defect type choices from the module
    defect_choices = []
    if hasattr(data_module, "_instance"):
        criteria = data_module.get_quality_criteria()
        seen = set()
        for c in criteria:
            if c.defect_type not in seen:
                defect_choices.append((c.defect_type, c.defect_type))
                seen.add(c.defect_type)

    formset = DefectFormSet(request.POST or None, form_kwargs={"defect_choices": defect_choices})
    results = []
    criteria = data_module.get_quality_criteria()

    if request.method == "POST" and formset.is_valid():
        defects = [f.cleaned_data for f in formset if f.cleaned_data and not f.cleaned_data.get("DELETE")]
        if defects:
            results = [data_module.evaluate_defect(d) for d in defects]

            # Save assessment record
            assessment = QualityAssessment.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_key="" if request.user.is_authenticated else request.session.session_key,
                normative_doc=doc,
                input_data={"defects": defects},
                results=results,
            )

            if request.POST.get("download_pdf"):
                return _download_results_pdf(request, doc, defects, results)

    return render(request, "quality/quality_assess.html", {
        "doc": doc,
        "formset": formset,
        "results": results,
        "criteria": criteria,
        "access_msg": access_msg,
    })


def _download_results_pdf(request, doc, defects, results):
    """Generate a PDF of quality assessment results."""
    from django.template.loader import render_to_string
    from apps.cards.services import generate_pdf_from_html

    html = render_to_string("quality/quality_results_pdf.html", {
        "doc": doc,
        "defects": defects,
        "results": results,
    }, request=request)
    try:
        pdf_bytes = generate_pdf_from_html(html)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="quality_assessment_{doc.pk}.pdf"'
        return response
    except Exception:
        messages.error(request, _("Ошибка генерации PDF."))
        return redirect("quality:assess", doc_id=doc.pk)
