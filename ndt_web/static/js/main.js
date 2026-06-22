/**
 * НК-Карта — основной JavaScript
 *
 * Динамические элементы формы, Ajax-запросы, валидация UI.
 */

'use strict';

document.addEventListener('DOMContentLoaded', function () {

  // ---- Авто-закрытие уведомлений ----
  document.querySelectorAll('.alert-dismissible').forEach(function (alert) {
    setTimeout(function () {
      var bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });

  // ---- Динамическое добавление/удаление дефектов ----
  initDefectsFormset();

  // ---- Динамическое обновление источников при изменении толщины ----
  initSourceSelector();

  // ---- Подтверждение удаления ----
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      if (!confirm(el.getAttribute('data-confirm'))) {
        e.preventDefault();
      }
    });
  });

  // ---- Показ/скрытие поля диаметра ----
  var objectTypeSelect = document.getElementById('id_object_type');
  if (objectTypeSelect) {
    toggleDiameterField(objectTypeSelect.value);
    objectTypeSelect.addEventListener('change', function () {
      toggleDiameterField(this.value);
    });
  }

  // ---- Подсказки для категорий шва ----
  var categorySelect = document.getElementById('id_weld_category');
  if (categorySelect) {
    categorySelect.addEventListener('change', function () {
      updateCategoryInfo(this.value);
    });
    // Инициализируем при загрузке
    updateCategoryInfo(categorySelect.value);
  }

  // ---- Инициализация всплывающих подсказок Bootstrap ----
  document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
    new bootstrap.Tooltip(el);
  });

});


/**
 * Показывает/скрывает поле наружного диаметра в зависимости от типа объекта.
 */
function toggleDiameterField(objectType) {
  var diameterGroup = document.getElementById('diameter-group');
  if (!diameterGroup) return;
  if (objectType === 'pipe') {
    diameterGroup.style.display = '';
  } else {
    diameterGroup.style.display = 'none';
  }
}


/**
 * Показывает информацию о категории сварного шва.
 */
var categoryDescriptions = {
  'I':   'Категория I — первый контур реакторной установки.',
  'II':  'Категория II — вспомогательные системы.',
  'III': 'Категория III — прочее оборудование.',
};

function updateCategoryInfo(category) {
  var infoEl = document.getElementById('category-info');
  if (!infoEl) return;
  var desc = categoryDescriptions[category] || '';
  infoEl.textContent = desc;
  infoEl.style.display = desc ? '' : 'none';
}


/**
 * Динамические источники излучения.
 * При изменении толщины стенки запрашивает подходящие источники через AJAX.
 */
function initSourceSelector() {
  var thicknessInput = document.getElementById('id_wall_thickness');
  var materialInput = document.getElementById('id_material');
  var sourceSelect = document.getElementById('id_source_code');
  var sourcesInfo = document.getElementById('sources-info');

  if (!thicknessInput || !sourceSelect) return;

  // Обновление при загрузке и изменении
  function updateSources() {
    var thickness = parseFloat(thicknessInput.value);
    if (!thickness || isNaN(thickness)) return;

    var url = '/ajax/sources/?thickness=' + thickness;
    if (materialInput && materialInput.value) {
      url += '&material=' + encodeURIComponent(materialInput.value);
    }

    fetch(url)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.sources) return;

        // Очищаем options кроме первого
        while (sourceSelect.options.length > 1) {
          sourceSelect.remove(1);
        }

        data.sources.forEach(function (src) {
          var opt = document.createElement('option');
          opt.value = src.code;
          opt.textContent = src.name;
          sourceSelect.appendChild(opt);
        });

        // Показываем информационный блок
        if (sourcesInfo) {
          if (data.sources.length > 0) {
            var tableRef = data.sources[0].table_ref || 'Б';
            var rangeLabel = data.sources[0].table_range_label || '';
            sourcesInfo.innerHTML =
              '<strong>По табл. ' + tableRef + ' ГОСТ Р 50.05.07-2018</strong>: ' +
              data.sources.length + ' допустимых источников' +
              (rangeLabel ? ' (диапазон: ' + rangeLabel + ')' : '') + '.';
            sourcesInfo.style.display = '';
          } else {
            sourcesInfo.innerHTML = 'Нет источников для данной толщины и материала по табл. Б.';
            sourcesInfo.style.display = '';
          }
        }
      })
      .catch(function (err) {
        console.warn('AJAX ошибка (источники):', err);
      });
  }

  thicknessInput.addEventListener('change', updateSources);
  thicknessInput.addEventListener('blur', updateSources);
  if (materialInput) {
    materialInput.addEventListener('change', updateSources);
  }
}


/**
 * Динамический набор форм дефектов (formset).
 */
function initDefectsFormset() {
  var container = document.getElementById('defects-container');
  var addBtn = document.getElementById('add-defect-btn');
  var countField = document.getElementById('defect_count');

  if (!container || !addBtn || !countField) return;

  var defectCount = parseInt(countField.value) || 1;

  addBtn.addEventListener('click', function () {
    var newBlock = createDefectBlock(defectCount);
    container.appendChild(newBlock);
    defectCount++;
    countField.value = defectCount;
    updateDefectLabels();
  });

  // Удаление через делегирование событий
  container.addEventListener('click', function (e) {
    var btn = e.target.closest('.remove-defect');
    if (!btn) return;
    var block = btn.closest('.defect-block');
    if (!block) return;

    // Не удаляем последний
    if (container.querySelectorAll('.defect-block').length <= 1) {
      alert('Добавьте хотя бы один дефект.');
      return;
    }
    block.remove();
    defectCount = container.querySelectorAll('.defect-block').length;
    countField.value = defectCount;
    rebuildDefectPrefixes();
    updateDefectLabels();
  });

  // Динамические подсказки по типу дефекта
  container.addEventListener('change', function (e) {
    if (e.target.classList.contains('defect-type-select')) {
      updateDefectFieldLabels(e.target);
    }
  });
}


/**
 * Создаёт новый блок ввода дефекта.
 */
function createDefectBlock(index) {
  var block = document.createElement('div');
  block.className = 'defect-block';
  block.dataset.index = index;

  block.innerHTML =
    '<button type="button" class="btn btn-sm btn-outline-danger remove-defect" ' +
    'title="Удалить дефект">✕</button>' +
    '<div class="row g-2">' +
      '<div class="col-md-4">' +
        '<label class="form-label">Тип дефекта</label>' +
        '<select name="defect_' + index + '-defect_type" class="form-select defect-type-select">' +
          '<option value="">— Выберите —</option>' +
          '<option value="crack">Трещина</option>' +
          '<option value="lack_of_fusion">Несплавление</option>' +
          '<option value="incomplete_penetration">Непровар</option>' +
          '<option value="pore">Пора (единичная)</option>' +
          '<option value="slag">Шлаковое включение</option>' +
          '<option value="tungsten">Вольфрамовое включение</option>' +
          '<option value="undercut">Подрез</option>' +
          '<option value="excess_penetration">Превышение проплава</option>' +
          '<option value="surface_defect">Поверхностный дефект</option>' +
        '</select>' +
      '</div>' +
      '<div class="col-md-3">' +
        '<label class="form-label size-1-label">Размер 1, мм</label>' +
        '<input type="number" name="defect_' + index + '-size_1" ' +
               'class="form-control size-1-field" step="0.1" min="0" value="0">' +
      '</div>' +
      '<div class="col-md-3">' +
        '<label class="form-label size-2-label">Размер 2, мм</label>' +
        '<input type="number" name="defect_' + index + '-size_2" ' +
               'class="form-control size-2-field" step="0.1" min="0" value="0">' +
      '</div>' +
      '<div class="col-md-2">' +
        '<label class="form-label">Кол-во</label>' +
        '<input type="number" name="defect_' + index + '-count" ' +
               'class="form-control" min="1" value="1">' +
      '</div>' +
    '</div>';

  return block;
}


/**
 * Пересобирает имена полей после удаления блока.
 */
function rebuildDefectPrefixes() {
  var blocks = document.querySelectorAll('#defects-container .defect-block');
  blocks.forEach(function (block, i) {
    block.dataset.index = i;
    block.querySelectorAll('input, select').forEach(function (field) {
      var name = field.getAttribute('name');
      if (name) {
        field.setAttribute('name', name.replace(/^defect_\d+/, 'defect_' + i));
      }
    });
  });
  document.getElementById('defect_count').value = blocks.length;
}


/**
 * Обновляет заголовки блоков.
 */
function updateDefectLabels() {
  var blocks = document.querySelectorAll('#defects-container .defect-block');
  // При необходимости можно добавить нумерацию
}


/**
 * Обновляет подсказки для полей размеров в зависимости от типа дефекта.
 */
var defectFieldHints = {
  'crack':                  { s1: 'Длина, мм', s2: '—' },
  'lack_of_fusion':         { s1: 'Длина, мм', s2: '—' },
  'incomplete_penetration': { s1: 'Длина, мм', s2: '—' },
  'pore':                   { s1: 'Диаметр, мм', s2: '—' },
  'slag':                   { s1: 'Длина, мм', s2: 'Ширина, мм' },
  'tungsten':               { s1: 'Диаметр, мм', s2: '—' },
  'undercut':               { s1: 'Глубина, мм', s2: 'Длина, мм' },
  'excess_penetration':     { s1: 'Высота, мм', s2: '—' },
  'surface_defect':         { s1: 'Высота, мм', s2: '—' },
};

function updateDefectFieldLabels(selectEl) {
  var block = selectEl.closest('.defect-block');
  if (!block) return;
  var hints = defectFieldHints[selectEl.value] || { s1: 'Размер 1, мм', s2: 'Размер 2, мм' };
  var s1Label = block.querySelector('.size-1-label');
  var s2Label = block.querySelector('.size-2-label');
  if (s1Label) s1Label.textContent = hints.s1;
  if (s2Label) s2Label.textContent = hints.s2;
}
