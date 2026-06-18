"""Dynamic forms for tech-card input data."""

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.standards.models import NormativeDocument
from ndt_data.base import FieldDefinition


def build_card_form_class(field_defs: list[FieldDefinition]):
    """Dynamically construct a Form class from FieldDefinition list."""
    fields = {}
    for fd in field_defs:
        if fd.field_type == "select":
            field = forms.ChoiceField(
                label=fd.label,
                choices=[("", "— выберите —")] + list(fd.choices),
                required=fd.required,
                help_text=fd.help_text,
            )
        elif fd.field_type == "number":
            field = forms.FloatField(
                label=f"{fd.label}{' (' + fd.unit + ')' if fd.unit else ''}",
                required=fd.required,
                help_text=fd.help_text,
                initial=fd.default,
            )
        elif fd.field_type == "textarea":
            field = forms.CharField(
                label=fd.label,
                widget=forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
                required=fd.required,
                help_text=fd.help_text,
            )
        elif fd.field_type == "checkbox":
            field = forms.BooleanField(
                label=fd.label,
                required=False,
                help_text=fd.help_text,
            )
        else:
            field = forms.CharField(
                label=fd.label,
                required=fd.required,
                help_text=fd.help_text,
                initial=fd.default,
            )

        # Apply Bootstrap styling
        if not isinstance(field.widget, (forms.CheckboxInput, forms.Select)):
            field.widget.attrs.setdefault("class", "form-control")
        elif isinstance(field.widget, forms.Select):
            field.widget.attrs.setdefault("class", "form-select")
        elif isinstance(field.widget, forms.CheckboxInput):
            field.widget.attrs.setdefault("class", "form-check-input")

        fields[fd.name] = field

    return type("DynamicCardForm", (forms.BaseForm,), {"base_fields": fields})


class DocumentSelectForm(forms.Form):
    """Step 1: Choose NDT method and normative document."""

    normative_doc = forms.ModelChoiceField(
        queryset=NormativeDocument.objects.filter(is_active=True, has_card_template=True),
        label=_("Нормативный документ"),
        empty_label=_("— выберите документ —"),
        widget=forms.Select(attrs={"class": "form-select form-select-lg"}),
    )
