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


SCHEME_CHOICES = [
    ('',     '— Выберите схему просвечивания —'),
    ('4_6',  'Чертёж 2 — плоские детали, листы, обечайки (источник с одной стороны)'),
    ('5a',   'Чертёж 3а — трубопровод, источник снаружи, просвечивание через 2 стенки'),
    ('5b',   'Чертёж 3б — трубопровод, источник снаружи, через 1 стенку (эллипс)'),
    ('5v',   'Чертёж 3в — трубопровод малого Ø (≤100 мм), источник снаружи по диаметру'),
    ('5g',   'Чертёж 3г — трубопровод Ø>50 мм, источник внутри со смещением от оси'),
    ('5d',   'Чертёж 3д — трубопровод Ø>50 мм, источник внутри (другой вариант)'),
    ('5zh',  'Чертёж 3ж — панорамный, источник на оси внутри трубы (Ø ≤ 2 м)'),
    ('5z',   'Чертёж 3и — источник внутри, трубопровод большого Ø (> 2 м)'),
]

SCHEME_IMAGES = {
    '4_6':  'img/scheme_4_6.png',
    '5a':   'img/scheme_5a.png',
    '5b':   'img/scheme_5b.png',
    '5v':   'img/scheme_5v.png',
    '5g':   'img/scheme_5g.png',
    '5d':   'img/scheme_5d.png',
    '5zh':  'img/scheme_5zh.png',
    '5z':   'img/scheme_5z.png',
}


class TechCardStep3Form(forms.Form):
    """Шаг 3: Источник излучения, схема и геометрия просвечивания."""

    scheme_type = forms.ChoiceField(
        choices=SCHEME_CHOICES,
        label='Схема просвечивания *',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_scheme_type'}),
        help_text=(
            'Выберите схему по типу объекта. '
            'Для трубопроводов — схемы 3а/3б/3в (источник снаружи) или 3г/3д/3ж (источник внутри). '
            'Для плоских деталей — Чертёж 2.'
        ),
    )
    source_code = forms.ChoiceField(
        choices=[('', '— Выберите источник —')] + get_source_choices(),
        label='Источник излучения *',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_source_code'}),
        help_text='Выберите источник в соответствии с толщиной металла.',
    )
    focal_spot_mm = forms.FloatField(
        min_value=0.1, max_value=20,
        label='Размер фокусного пятна (Φ), мм *',
        initial=2.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'min': '0.1',
            'placeholder': '2.0',
        }),
        help_text='Указывается в паспорте источника. Для рентгеновского аппарата — из технических данных.',
    )
    source_activity = forms.CharField(
        max_length=100, required=False,
        label='Активность источника',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '10 Ки (Ir-192) или по паспорту',
        }),
        help_text='Укажите из паспорта источника. Используется для расчёта времени экспозиции.',
    )
    film_length_mm = forms.FloatField(
        required=False,
        min_value=50, max_value=1000,
        label='Длина снимка (l), мм',
        initial=350,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '10',
            'placeholder': '350',
            'id': 'id_film_length_mm',
        }),
        help_text='Только для схемы 3б (чертёж 3б). Длина кассеты с плёнкой в мм.',
    )
    ofd_mm = forms.FloatField(
        min_value=0, max_value=200,
        label='Расстояние объект–детектор (b), мм',
        initial=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.5',
            'min': '0',
            'placeholder': '5',
        }),
        help_text=(
            'Расстояние от поверхности объекта до детектора (плёнки). '
            'При прижатой кассете — 0–5 мм.'
        ),
    )
    film_name = forms.ChoiceField(
        choices=[('', '— Выберите плёнку —')] + get_film_choices(),
        required=False,
        label='Тип радиографической плёнки',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Тип плёнки определяется классом контроля. Можно не выбирать — подберётся автоматически.',
    )


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
