"""Views for tech-card creation, listing, download and deletion."""

import mimetypes

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.standards.models import NormativeDocument
from .forms import DocumentSelectForm, build_card_form_class
from .models import TechCard
from .services import can_create_card, create_tech_card


@login_required
def card_wizard_step1(request):
    """Step 1: select normative document."""
    form = DocumentSelectForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        doc = form.cleaned_data["normative_doc"]
        return redirect("cards:wizard_step2", doc_id=doc.pk)
    return render(request, "cards/wizard_step1.html", {"form": form})


@login_required
def card_wizard_step2(request, doc_id):
    """Step 2: fill tech-card input fields."""
    doc = get_object_or_404(NormativeDocument, pk=doc_id, is_active=True)
    data_module = doc.get_data_module()

    if data_module is None:
        messages.error(request, _("Модуль данных для данного документа ещё не реализован."))
        return redirect("cards:wizard_step1")

    allowed, reason, is_free = can_create_card(request.user, doc)
    field_defs = data_module.get_card_fields()
    FormClass = build_card_form_class(field_defs)
    form = FormClass(request.POST or None)

    if request.method == "POST" and form.is_valid():
        if not allowed:
            messages.error(request, reason)
            return redirect("payments:tariffs")

        try:
            card = create_tech_card(request.user, doc, form.cleaned_data)
            messages.success(request, _("Технологическая карта успешно создана!"))
            return redirect("cards:card_detail", pk=card.pk)
        except (PermissionError, ValueError) as exc:
            messages.error(request, str(exc))
            return redirect("payments:tariffs")
        except Exception as exc:
            messages.error(request, _("Произошла ошибка при создании техкарты. Попробуйте ещё раз."))

    return render(request, "cards/wizard_step2.html", {
        "form": form,
        "doc": doc,
        "allowed": allowed,
        "access_reason": reason,
        "is_free": is_free,
        "field_defs": field_defs,
    })


@login_required
def card_detail(request, pk):
    """View a generated tech card."""
    card = get_object_or_404(TechCard, pk=pk, user=request.user)
    return render(request, "cards/card_detail.html", {"card": card})


@login_required
def card_download_docx(request, pk):
    """Download the DOCX file."""
    card = get_object_or_404(TechCard, pk=pk, user=request.user)
    if not card.docx_file:
        raise Http404
    response = FileResponse(card.docx_file.open("rb"), as_attachment=True,
                            filename=f"techcard_{card.pk}.docx")
    return response


@login_required
def card_download_pdf(request, pk):
    """Download the PDF file, generating it on-the-fly if needed."""
    from django.template.loader import render_to_string
    from django.core.files.base import ContentFile
    from .services import generate_pdf_from_html

    card = get_object_or_404(TechCard, pk=pk, user=request.user)

    if not card.pdf_file:
        # Generate PDF from HTML template
        html = render_to_string("cards/card_pdf.html", {"card": card})
        try:
            pdf_bytes = generate_pdf_from_html(html)
            card.pdf_file.save(f"{card.id}.pdf", ContentFile(pdf_bytes), save=True)
        except Exception:
            return HttpResponse("Ошибка генерации PDF", status=500)

    response = FileResponse(card.pdf_file.open("rb"), as_attachment=True,
                            filename=f"techcard_{card.pk}.pdf")
    response["Content-Type"] = "application/pdf"
    return response


@login_required
@require_POST
def card_delete(request, pk):
    """Delete a tech card."""
    card = get_object_or_404(TechCard, pk=pk, user=request.user)
    card.delete()
    messages.success(request, _("Техкарта удалена."))
    return redirect("accounts:cabinet")


def card_example(request):
    """Public demo of a sample tech card (no login required)."""
    return render(request, "cards/card_example.html")
