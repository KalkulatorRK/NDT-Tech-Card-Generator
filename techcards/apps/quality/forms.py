"""Forms for quality assessment."""

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.standards.models import NormativeDocument


class QualityDocumentForm(forms.Form):
    """Step 1: choose document for quality assessment."""

    normative_doc = forms.ModelChoiceField(
        queryset=NormativeDocument.objects.filter(is_active=True, has_quality_criteria=True),
        label=_("Нормативный документ"),
        empty_label=_("— выберите документ —"),
        widget=forms.Select(attrs={"class": "form-select form-select-lg"}),
    )


class DefectForm(forms.Form):
    """Single defect entry for quality assessment."""

    defect_type = forms.CharField(
        label=_("Тип дефекта"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    size_mm = forms.FloatField(
        label=_("Размер (мм)"),
        min_value=0,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    count = forms.IntegerField(
        label=_("Количество"),
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    weld_category = forms.ChoiceField(
        label=_("Категория шва"),
        choices=[("I", "I"), ("II", "II"), ("III", "III"), ("IV", "IV")],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    thickness_mm = forms.FloatField(
        label=_("Толщина металла (мм)"),
        min_value=0.5,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.5"}),
    )

    def __init__(self, *args, defect_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if defect_choices:
            self.fields["defect_type"].widget = forms.Select(
                choices=[("", "— тип дефекта —")] + list(defect_choices),
                attrs={"class": "form-select"},
            )


DefectFormSet = forms.formset_factory(DefectForm, extra=1, max_num=20)
