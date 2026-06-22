"""
Формы приложения «Технологические карты».

Форма ввода исходных данных для генерации технологической карты
радиографического контроля по ГОСТ Р 50.05.07-2018.
"""

from django import forms
from normative.gost_50_05_07 import (
    get_source_choices,     get_film_choices, get_iqi_choices, get_film_size_choices,
    get_suitable_films,
)
from .scheme_display import SCHEME_CHOICES, SCHEME_HELP_TEXT
from normative.gost_59023_2 import (
    get_joint_type_choices, get_welding_process_choices,
    get_controlled_object_material_choices, get_material_choices,
    get_pipe_diameters, JOINT_TYPES, MATERIAL_CLASS_CHOICES,
    MATERIAL_TITANIUM, MATERIAL_ALUMINUM, requires_material_grade,
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
    """Шаг 2: Материал, геометрия объекта и тип сварного соединения."""

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
        choices=[('', '— Выберите материал —')] + get_controlled_object_material_choices(),
        label='Материал контролируемого объекта *',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_material'}),
    )

    # Марка основного металла (для сплавов Ti/Al или своей марки стали)
    material_custom = forms.CharField(
        required=False,
        label='Марка основного металла',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: ВТ6, АМг6 или 09ХН10Т',
            'id': 'id_material_custom',
        }),
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
        help_text='Указывается только для трубопроводов.',
    )
    # Условное обозначение сварного соединения (ГОСТ Р 59023.2-2020)
    joint_designation = forms.ChoiceField(
        choices=get_joint_type_choices(),
        label='Условное обозначение сварного соединения (ГОСТ Р 59023.2-2020) *',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_joint_designation',
        }),
        help_text=(
            'С — стыковое, У — угловое, Т — тавровое. '
            'Номер определяет тип разделки кромок.'
        ),
    )
    welding_process = forms.ChoiceField(
        choices=[('', '— Выберите способ сварки —')] + get_welding_process_choices(),
        required=False,
        label='Способ сварки (код по ГОСТ Р 59023.2-2020) *',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_welding_process'}),
        help_text=(
            '10 — АДФ под флюсом; 30 — РДС; 40 — комбинированная; '
            '51/52 — аргонодуговая; 60 — ЭЛС'
        ),
    )
    welding_process_custom = forms.CharField(
        required=False,
        label='Или введите код/вид сварки вручную',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: 70 — плазменная, или собственное обозначение',
        }),
    )
    weld_category = forms.ChoiceField(
        choices=get_category_choices(),
        label='Категория сварного соединения (по НП-104-18) *',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_weld_category'}),
        help_text=(
            'Категория I — первый контур АЭУ. '
            'Категория II — вспомогательные системы. '
            'Категория III — прочее оборудование.'
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

    def clean(self):
        cleaned = super().clean()
        material = cleaned.get('material', '')
        grade = (cleaned.get('material_custom') or '').strip()
        if requires_material_grade(material) and not grade:
            self.add_error(
                'material_custom',
                'Укажите марку основного металла для выбранного типа сплава.',
            )
        elif not material and grade:
            cleaned['material'] = grade
        cleaned['material_custom'] = grade
        return cleaned

    def clean_joint_designation(self):
        """Проверяем что обозначение шва выбрано."""
        designation = self.cleaned_data.get('joint_designation')
        if not designation:
            raise forms.ValidationError('Выберите условное обозначение сварного соединения.')
        return designation


class TechCardStep3Form(forms.Form):
    """Шаг 3: Источник излучения, схема и геометрия просвечивания."""

    def __init__(self, *args, wall_thickness=None, material_type='steel', **kwargs):
        super().__init__(*args, **kwargs)
        self._allowed_films = []
        if wall_thickness is not None:
            source_code = None
            if self.data:
                source_code = self.data.get('source_code') or None
            self._allowed_films = get_suitable_films(
                float(wall_thickness), material_type, source_code,
            )
            if self._allowed_films:
                self.fields['film_name'].choices = (
                    [('', '— Выберите плёнку —')]
                    + [(f, f) for f in self._allowed_films]
                )
                self.fields['film_name'].help_text = (
                    'Допустимые плёнки по табл. Б ГОСТ Р 50.05.07-2018 '
                    'для выбранного источника и толщины.'
                )

    scheme_type = forms.ChoiceField(
        choices=SCHEME_CHOICES,
        label='Схема просвечивания *',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_scheme_type'}),
        help_text=SCHEME_HELP_TEXT,
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
    film_size = forms.ChoiceField(
        choices=[('', '— Выберите размер —')] + get_film_size_choices(),
        required=False,
        label='Размер плёнки (длина × ширина), мм',
        initial='240x100',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_film_size',
        }),
        help_text='Типовые размеры плёнки. Используется для схемы 3б и поля 5.7 техкарты.',
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
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_film_name'}),
        help_text='Список формируется по табл. Б после выбора источника излучения.',
    )
    film_name_custom = forms.CharField(
        required=False,
        label='Или введите тип плёнки вручную',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: РТ-4МС или другая плёнка',
            'id': 'id_film_name_custom',
        }),
    )

    def clean(self):
        cleaned = super().clean()
        film = cleaned.get('film_name')
        custom = (cleaned.get('film_name_custom') or '').strip()
        cleaned['film_name_custom'] = custom
        if custom and not film:
            cleaned['film_name'] = custom
        elif film and self._allowed_films and film not in self._allowed_films:
            self.add_error(
                'film_name',
                'Выберите плёнку из списка табл. Б или укажите свой вариант вручную.',
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
