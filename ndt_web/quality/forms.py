"""
Формы приложения «Оценка качества».

Форма ввода параметров сварного соединения и дефектов.
"""

from django import forms
from normative.np_104_18 import get_choices as get_category_choices


NORMATIVE_DOC_CHOICES = [
    ('НП-105-18', 'НП-105-18 — Требования к качеству сварных соединений АЭУ'),
]

WELD_CATEGORY_CHOICES = get_category_choices()


class QualityAssessmentForm(forms.Form):
    """Главная форма оценки качества."""

    normative_doc = forms.ChoiceField(
        choices=NORMATIVE_DOC_CHOICES,
        label='Нормативный документ *',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    weld_category = forms.ChoiceField(
        choices=WELD_CATEGORY_CHOICES,
        label='Категория сварного соединения (по НП-104-18) *',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Категория I — первый контур АЭУ; IV — вспомогательные конструкции.',
    )
    wall_thickness = forms.FloatField(
        min_value=0.5, max_value=500,
        label='Толщина стенки, мм *',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.5',
            'placeholder': '10',
            'min': '0.5',
        }),
    )
    weld_length = forms.FloatField(
        required=False, min_value=1, max_value=100000,
        label='Длина шва, мм (для оценки подрезов)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '1',
            'placeholder': '500',
        }),
        help_text='Необходимо для оценки суммарной длины подрезов.',
    )


DEFECT_TYPE_CHOICES_FORM = [
    ('', '— Выберите тип дефекта —'),
    ('crack', 'Трещина'),
    ('lack_of_fusion', 'Несплавление'),
    ('incomplete_penetration', 'Непровар'),
    ('pore', 'Пора (единичная)'),
    ('slag', 'Шлаковое включение'),
    ('tungsten', 'Вольфрамовое включение'),
    ('undercut', 'Подрез'),
    ('excess_penetration', 'Превышение проплава'),
    ('surface_defect', 'Поверхностный дефект'),
]


class DefectEntryForm(forms.Form):
    """Форма ввода данных об одном дефекте (используется в formset)."""

    defect_type = forms.ChoiceField(
        choices=DEFECT_TYPE_CHOICES_FORM,
        label='Тип дефекта',
        widget=forms.Select(attrs={'class': 'form-select defect-type-select'}),
    )
    size_1 = forms.FloatField(
        min_value=0, max_value=1000,
        label='Размер 1, мм',
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control size-1-field',
            'step': '0.1',
            'placeholder': '0',
            'min': '0',
        }),
        help_text='Диаметр поры / глубина подреза / высота проплава / длина дефекта',
    )
    size_2 = forms.FloatField(
        required=False,
        min_value=0, max_value=1000,
        label='Размер 2, мм',
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control size-2-field',
            'step': '0.1',
            'placeholder': '0',
            'min': '0',
        }),
        help_text='Ширина шлакового включения / длина подреза',
    )
    count = forms.IntegerField(
        min_value=1, max_value=999,
        label='Количество',
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'placeholder': '1',
        }),
    )

    def clean_defect_type(self):
        dt = self.cleaned_data.get('defect_type')
        if not dt:
            raise forms.ValidationError('Выберите тип дефекта.')
        return dt
