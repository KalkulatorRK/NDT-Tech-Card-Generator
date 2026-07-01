"""
Формы приложения «Технологические карты».

Форма ввода исходных данных для генерации технологической карты
радиографического контроля по ГОСТ Р 50.05.07-2018.
"""

from django import forms
from django.utils import timezone
from normative.gost_50_05_07 import (
    get_film_choices, get_iqi_choices,
    get_suitable_films, get_suitable_sources,
)
from .scheme_display import (
    SCHEME_CHOICES, SCHEME_HELP_TEXT, get_scheme_choices_for_object_type,
    get_schemes_for_object_type,
)
from normative.gost_59023_2 import (
    get_joint_type_choices, get_welding_process_choices,
    get_welding_process_choices_for_joint,
    get_controlled_object_material_choices, get_material_choices,
    get_welding_material_choices,
    get_pipe_diameters, JOINT_TYPES, MATERIAL_CLASS_CHOICES,
    MATERIAL_TITANIUM, MATERIAL_ALUMINUM, requires_material_grade,
    resolve_material_type,
)
from normative.np_105_18 import get_weld_category_choices


class TechCardStep1Form(forms.Form):
    """Шаг 1: Идентификация объекта контроля."""

    SIGNATURE_POSITION_CHOICES = [
        ('', '— Выберите должность —'),
        ('Ведущий инженер технолог', 'Ведущий инженер технолог'),
        ('Инженер-технолог', 'Инженер-технолог'),
        ('Начальник лаборатории НК', 'Начальник лаборатории НК'),
        ('Руководитель группы НК', 'Руководитель группы НК'),
        ('__custom__', 'Другая (ввести вручную)'),
    ]

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

    developed_by_position = forms.ChoiceField(
        choices=SIGNATURE_POSITION_CHOICES,
        required=False,
        label='Разработал — должность',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_developed_by_position'}),
    )
    developed_by_position_custom = forms.CharField(
        required=False,
        label='Разработал — должность (вручную)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ведущий инженер технолог'}),
    )
    developed_by_name = forms.CharField(
        max_length=200, required=False,
        label='Разработал — ФИО',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Петров П.П.'}),
    )
    develop_date = forms.DateField(
        required=False,
        label='Разработал — дата',
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    developed_by_certificate = forms.CharField(
        max_length=100, required=False,
        label='Разработал — удостоверение №',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'НК-0000'}),
    )
    checked_by_position = forms.ChoiceField(
        choices=SIGNATURE_POSITION_CHOICES,
        required=False,
        label='Проверил — должность',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_checked_by_position'}),
    )
    checked_by_position_custom = forms.CharField(
        required=False,
        label='Проверил — должность (вручную)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Начальник лаборатории НК'}),
    )
    checked_by_name = forms.CharField(
        max_length=200, required=False,
        label='Проверил — ФИО',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Сидоров С.С.'}),
    )
    check_date = forms.DateField(
        required=False,
        label='Проверил — дата',
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    checked_by_certificate = forms.CharField(
        max_length=100, required=False,
        label='Проверил — удостоверение №',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'НК-0000'}),
    )

    def clean(self):
        cleaned = super().clean()
        for prefix in ('developed_by', 'checked_by'):
            pos = cleaned.get(f'{prefix}_position', '')
            custom = (cleaned.get(f'{prefix}_position_custom') or '').strip()
            if pos == '__custom__' and not custom:
                self.add_error(
                    f'{prefix}_position_custom',
                    'Укажите должность вручную или выберите из списка.',
                )
            elif pos and pos != '__custom__':
                cleaned[f'{prefix}_position_resolved'] = pos
            elif custom:
                cleaned[f'{prefix}_position_resolved'] = custom
            else:
                cleaned[f'{prefix}_position_resolved'] = ''
        return cleaned


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
        choices=[('', '— Выберите способ сварки —')],
        required=False,
        label='Способ сварки (код по ГОСТ Р 59023.2-2020) *',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_welding_process'}),
        help_text='Список ограничен допустимыми способами для выбранного типа соединения.',
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
        choices=get_weld_category_choices(),
        label='Категория сварного соединения (по НП-105-18) *',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_weld_category'}),
    )
    joint_mobility = forms.ChoiceField(
        choices=[
            ('non_rotating', 'Неповоротное'),
            ('rotating', 'Поворотное'),
        ],
        initial='non_rotating',
        label='Поворотность сварного соединения',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        help_text='Влияет на нормы оценки по табл. 4.4 и 4.6 НП-105-18.',
    )
    welding_material = forms.ChoiceField(
        choices=get_welding_material_choices(),
        required=False,
        label='Марка сварочного материала',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_welding_material'}),
        help_text='По умолчанию совпадает с основным металлом (п. 1.9).',
    )
    welding_material_custom = forms.CharField(
        required=False,
        label='Марка сварочного материала (вручную)',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Например: ЭА-400/10Х',
            'id': 'id_welding_material_custom',
        }),
    )
    flat_length_mm = forms.FloatField(
        required=False, min_value=0, max_value=50000,
        label='Длина листа / пластины, мм',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'placeholder': '1500',
            'id': 'id_flat_length_mm',
        }),
        help_text='Для плоских деталей. Для трубопровода — прочерк.',
    )
    reinforcement_removed = forms.BooleanField(
        required=False,
        label='Валик усиления снят',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_reinforcement_removed'}),
        help_text='Если отмечено, высота g не учитывается в расчётах K и f.',
    )
    has_backing_ring = forms.BooleanField(
        required=False,
        label='Подкладное кольцо',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_has_backing_ring'}),
    )
    backing_ring_thickness_mm = forms.FloatField(
        required=False, min_value=0.1, max_value=500,
        label='Толщина стенки подкладного кольца, мм',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'placeholder': '3.0',
            'id': 'id_backing_ring_thickness_mm',
        }),
        help_text='Учитывается при расчёте K и f при контроле через одну стенку.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        joint = ''
        material = ''
        if self.is_bound:
            joint = self.data.get('joint_designation', '')
            material = self.data.get('material', '')
        else:
            joint = self.initial.get('joint_designation', '')
            material = self.initial.get('material', '')
        if joint:
            self.fields['welding_process'].choices = (
                get_welding_process_choices_for_joint(joint)
            )
        material_type = resolve_material_type(material)
        self.fields['weld_category'].choices = get_weld_category_choices(material_type)

    def clean_outer_diameter(self):
        """Диаметр обязателен для трубопровода."""
        obj_type = self.data.get('object_type', 'flat')
        diameter = self.cleaned_data.get('outer_diameter')
        if obj_type == 'pipe' and not diameter:
            raise forms.ValidationError(
                'Для трубопровода необходимо указать наружный диаметр.'
            )
        if obj_type != 'pipe':
            return None
        return diameter

    def clean_flat_length_mm(self):
        obj_type = self.data.get('object_type', 'flat')
        length = self.cleaned_data.get('flat_length_mm')
        if obj_type == 'flat' and not length:
            return None
        return length

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

        joint = cleaned.get('joint_designation', '')
        process = (cleaned.get('welding_process') or '').strip()
        custom_process = (cleaned.get('welding_process_custom') or '').strip()
        if joint and process:
            allowed = JOINT_TYPES.get(joint, {}).get('methods', [])
            if process not in allowed:
                self.add_error(
                    'welding_process',
                    'Выбранный способ сварки не допускается для данного типа соединения '
                    f'по ГОСТ Р 59023.2-2020 (допустимо: {", ".join(allowed)}).',
                )
        elif joint and not process and not custom_process:
            self.add_error(
                'welding_process',
                'Выберите способ сварки из списка допустимых для выбранного соединения.',
            )

        if cleaned.get('has_backing_ring') and not cleaned.get('backing_ring_thickness_mm'):
            cleaned['backing_ring_thickness_mm'] = cleaned.get('wall_thickness')

        material_type = resolve_material_type(cleaned.get('material', ''))
        weld_cat = cleaned.get('weld_category')
        if weld_cat in ('Iн', 'IIн') and material_type != 'steel':
            self.add_error(
                'weld_category',
                'Категории Iн и IIн применимы только для стальных сварных соединений '
                '(табл. 4.9 НП-105-18).',
            )

        return cleaned

    def clean_joint_designation(self):
        """Проверяем что обозначение шва выбрано."""
        designation = self.cleaned_data.get('joint_designation')
        if not designation:
            raise forms.ValidationError('Выберите условное обозначение сварного соединения.')
        return designation


class TechCardStep3Form(forms.Form):
    """Шаг 3: Источник излучения, схема и геометрия просвечивания."""

    IQI_SIDE_CHOICES = [
        ('source', 'Со стороны источника'),
        ('film', 'Со стороны плёнки'),
    ]

    def __init__(self, *args, wall_thickness=None, material_type='steel',
                 joint_designation='', welding_process='30', object_type='pipe',
                 **kwargs):
        super().__init__(*args, **kwargs)
        self._wall_thickness = wall_thickness
        self._material_type = material_type
        self._joint_designation = joint_designation
        self._welding_process = welding_process
        self._object_type = object_type
        self._allowed_schemes = set(get_schemes_for_object_type(object_type))
        self.fields['scheme_type'].choices = get_scheme_choices_for_object_type(object_type)
        if len(self._allowed_schemes) == 1 and not self.is_bound:
            self.fields['scheme_type'].initial = next(iter(self._allowed_schemes))
        self._allowed_films = []
        self._allowed_source_codes = set()
        self._table_b_thickness = None

        source_code_init = None
        if self.data:
            source_code_init = (self.data.get('source_code') or '').strip() or None
        elif self.initial.get('source_code'):
            source_code_init = self.initial.get('source_code')

        if source_code_init:
            from normative.gost_50_05_07 import RADIATION_SOURCES
            src_info = next(
                (s for s in RADIATION_SOURCES if s['code'] == source_code_init), None,
            )
            src_type = src_info.get('type', 'isotope') if src_info else 'isotope'
            if src_type == 'isotope' and not self.is_bound:
                self.fields['focal_spot_mm'].initial = 3.0

        scheme = None
        source_code = None
        if self.data:
            scheme = (self.data.get('scheme_type') or '').strip() or None
            source_code = (self.data.get('source_code') or '').strip() or None

        if wall_thickness is not None and scheme:
            from normative.calculations import resolve_table_b_thickness_mm
            rad = resolve_table_b_thickness_mm(
                float(wall_thickness), scheme, joint_designation, welding_process,
            )
            self._table_b_thickness = rad['table_b_thickness_mm']
            self._allowed_source_codes = {
                s['code'] for s in get_suitable_sources(
                    self._table_b_thickness, material_type,
                )
            }
            self._allowed_films = get_suitable_films(
                self._table_b_thickness, material_type, source_code,
            )
            if self._allowed_films:
                self.fields['film_name'].choices = (
                    [('', '— Выберите плёнку —')]
                    + [(f, f) for f in self._allowed_films]
                )
                self.fields['film_name'].help_text = (
                    'Допустимые плёнки по табл. Б ГОСТ Р 50.05.07-2018 '
                    'для выбранного источника и радиационной толщины.'
                )

    scheme_type = forms.ChoiceField(
        choices=SCHEME_CHOICES,
        label='Схема просвечивания *',
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_scheme_type'}),
        help_text=SCHEME_HELP_TEXT,
    )
    iqi_side = forms.ChoiceField(
        choices=IQI_SIDE_CHOICES,
        initial='source',
        label='Положение ИКИ (эталона)',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        help_text=(
            'При установке ИКИ со стороны плёнки проволочный эталон подбирается '
            'на одну ступень жёстче относительно требуемой чувствительности K '
            '(ГОСТ Р 50.05.07-2018, п. 6.1.11).'
        ),
    )
    source_code = forms.CharField(
        required=True,
        label='Источник излучения *',
        widget=forms.HiddenInput(attrs={'id': 'id_source_code'}),
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

    def clean(self):
        cleaned = super().clean()
        scheme = (cleaned.get('scheme_type') or '').strip()
        source = (cleaned.get('source_code') or '').strip()
        cleaned['source_code'] = source
        film = cleaned.get('film_name')

        if not scheme:
            self.add_error('scheme_type', 'Выберите схему просвечивания.')
            return cleaned

        if scheme not in self._allowed_schemes:
            self.add_error(
                'scheme_type',
                'Выбранная схема не соответствует типу объекта контроля.',
            )
            return cleaned

        if not source:
            self.add_error('source_code', 'Выберите источник излучения из рекомендованных.')
        elif self._allowed_source_codes and source not in self._allowed_source_codes:
            self.add_error(
                'source_code',
                'Выберите источник из списка, допустимого по табл. Б для рассчитанной радиационной толщины.',
            )

        if film and self._allowed_films and film not in self._allowed_films:
            self.add_error(
                'film_name',
                'Выберите плёнку из списка, сформированного по табл. Б.',
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
