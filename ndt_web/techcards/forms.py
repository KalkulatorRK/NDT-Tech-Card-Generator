"""
Формы приложения «Технологические карты».

Форма ввода исходных данных для генерации технологической карты
радиографического контроля по ГОСТ Р 50.05.07-2018.
"""

from django import forms
from normative.gost_50_05_07 import get_source_choices, get_film_choices, get_iqi_choices
from normative.gost_59023_2 import (
    get_joint_type_choices, get_welding_process_choices, get_material_choices,
    get_pipe_diameters,
)
from normative.np_104_18 import get_choices as get_category_choices


class TechCardStep1Form(forms.Form):
    """Шаг 1: Идентификация объекта контроля."""

    organization = forms.CharField(
        max_length=255, required=False,
        label='Организация',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ООО «Атомстрой»'}),
    )
    object_name = forms.CharField(
        max_length=500, required=True,
        label='Наименование объекта контроля *',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Трубопровод подачи теплоносителя',
        }),
    )
    drawing_number = forms.CharField(
        max_length=100, required=False,
        label='Номер чертежа (схемы)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ТП-001-2024'}),
    )
    weld_number = forms.CharField(
        max_length=100, required=True,
        label='Номер (обозначение) сварного соединения *',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ш-01'}),
    )
    card_number = forms.CharField(
        max_length=50, required=False,
        label='Номер технологической карты',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ТК-РГК-001'}),
    )
    inspector_name = forms.CharField(
        max_length=200, required=False,
        label='Специалист НК (ФИО)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иванов Иван Иванович'}),
    )


class TechCardStep2Form(forms.Form):
    """Шаг 2: Материал и геометрия объекта."""

    OBJECT_TYPE_CHOICES = [
        ('pipe', 'Трубопровод (кольцевой шов)'),
        ('flat', 'Плоская деталь / пластина / лист'),
        ('vessel', 'Сосуд давления / обечайка'),
    ]

    object_type = forms.ChoiceField(
        choices=OBJECT_TYPE_CHOICES,
        label='Тип объекта контроля *',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_object_type'}),
    )
    material = forms.ChoiceField(
        choices=[('', '— Выберите марку стали —')] + get_material_choices(),
        label='Марка стали *',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    wall_thickness = forms.FloatField(
        min_value=0.5, max_value=500,
        label='Толщина стенки, мм *',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.5',
            'placeholder': '10',
            'min': '0.5',
            'max': '500',
        }),
        help_text='Для разнотолщинных соединений указывается большая толщина.',
    )
    outer_diameter = forms.FloatField(
        required=False, min_value=0, max_value=5000,
        label='Наружный диаметр трубопровода, мм',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'placeholder': '219.1',
            'min': '0',
        }),
        help_text='Указывается только для трубопроводов. Выберите значение из типоряда.',
    )
    weld_type = forms.ChoiceField(
        choices=get_joint_type_choices(),
        label='Тип сварного соединения *',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    welding_process = forms.ChoiceField(
        choices=[('', '— Выберите вид сварки —')] + get_welding_process_choices(),
        required=False,
        label='Вид сварки',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    weld_category = forms.ChoiceField(
        choices=get_category_choices(),
        label='Категория сварного соединения (по НП-104-18) *',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_weld_category'}),
        help_text=(
            'Категория I — первый контур реакторной установки. '
            'Категория II — вспомогательные системы. '
            'Категория III/IV — прочее оборудование.'
        ),
    )

    def clean_outer_diameter(self):
        """Диаметр обязателен для трубопровода."""
        obj_type = self.data.get('object_type', 'flat')
        diameter = self.cleaned_data.get('outer_diameter')
        if obj_type == 'pipe' and not diameter:
            raise forms.ValidationError(
                'Для трубопровода необходимо указать наружный диаметр.'
            )
        return diameter


class TechCardStep3Form(forms.Form):
    """Шаг 3: Параметры источника и геометрия просвечивания."""

    source_code = forms.ChoiceField(
        choices=[('', '— Выберите источник —')] + get_source_choices(),
        label='Источник излучения *',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_source_code'}),
        help_text='Выберите источник в соответствии с толщиной металла.',
    )
    focal_spot_mm = forms.FloatField(
        min_value=0.1, max_value=20,
        label='Размер фокусного пятна (d), мм *',
        initial=2.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'min': '0.1',
            'placeholder': '2.0',
        }),
        help_text='Указывается в паспорте источника. Для аппарата — из технических данных.',
    )
    source_activity = forms.CharField(
        max_length=100, required=False,
        label='Активность / мощность экспозиционной дозы',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '5 Ки (Ir-192) или по паспорту',
        }),
        help_text='Введите значение из паспорта источника или оставьте пустым для заполнения вручную.',
    )
    sfd_mm = forms.FloatField(
        min_value=100, max_value=5000,
        label='Расстояние источник–детектор (SFD, f), мм *',
        initial=700,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '10',
            'min': '100',
            'placeholder': '700',
        }),
        help_text='Расстояние от источника излучения до детектора (плёнки).',
    )
    ofd_mm = forms.FloatField(
        min_value=0, max_value=200,
        label='Расстояние объект–детектор (OFD, b), мм *',
        initial=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.5',
            'min': '0',
            'placeholder': '5',
        }),
        help_text=(
            'Расстояние от контролируемой поверхности объекта до детектора. '
            'Для плоских деталей без зазора — 0.'
        ),
    )
    film_name = forms.ChoiceField(
        choices=[('', '— Выберите плёнку —')] + get_film_choices(),
        required=False,
        label='Тип радиографической плёнки',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Тип плёнки определяется классом контроля и подбирается автоматически.',
    )

    def clean(self):
        """Проверяет, что OFD < SFD."""
        cleaned = super().clean()
        sfd = cleaned.get('sfd_mm', 0)
        ofd = cleaned.get('ofd_mm', 0)
        if sfd and ofd and ofd >= sfd:
            self.add_error(
                'ofd_mm',
                'Расстояние объект–детектор (OFD) должно быть меньше '
                'расстояния источник–детектор (SFD).'
            )
        return cleaned


class TechCardConfirmForm(forms.Form):
    """
    Шаг 4: Подтверждение корректности введённых данных.
    Пользователь явно подтверждает достоверность данных перед генерацией.
    """

    confirm_data = forms.BooleanField(
        required=True,
        label=(
            'Подтверждаю корректность всех введённых данных. '
            'Я понимаю, что от правильности исходных данных зависит '
            'точность разработанной технологической карты.'
        ),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
    confirm_normative = forms.BooleanField(
        required=True,
        label=(
            'Подтверждаю, что объект контроля и условия его применения '
            'соответствуют области применения ГОСТ Р 50.05.07-2018.'
        ),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )
