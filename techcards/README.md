# НКТехКарты — Система автоматической разработки технологических карт НК

Веб-приложение на Django для автоматизации разработки технологических карт
неразрушающего контроля (НК) и оценки качества сварных соединений.

## Возможности

- **Разработка техкарт** — автоматическое создание технологических карт НК по нормативным документам (ГОСТ, НП, РД) с генерацией файлов DOCX и PDF
- **Оценка качества** — автоматическая оценка допустимости дефектов сварных соединений
- **Личный кабинет** — хранение, просмотр, скачивание и управление готовыми техкартами
- **Платёжная система** — интеграция ЮKassa для оплаты тарифных планов
- **Ролевой доступ** — Администратор, Зарегистрированный пользователь, Гость

## Поддерживаемые нормативные документы

| Метод НК | Документы |
|---|---|
| ВИК | РД 03-606-03, ГОСТ Р ИСО 17637-2014 |
| РК | ГОСТ 7512-82, НП-105-18 |
| ПВК | ГОСТ Р ИСО 3452-1-2011 |
| КГ | ГОСТ Р 52005-2003 |

## Технологический стек

- **Backend**: Python 3.12, Django 5.1
- **Frontend**: Bootstrap 5.3, Bootstrap Icons
- **БД**: PostgreSQL (SQLite для разработки)
- **Документы**: python-docx (DOCX), xhtml2pdf (PDF)
- **Аутентификация**: django-allauth
- **Платежи**: YooKassa SDK

## Установка и запуск

### 1. Установить зависимости

```bash
pip install -r requirements.txt
```

### 2. Настроить переменные окружения

```bash
cp .env.example .env
# Отредактируйте .env — укажите SECRET_KEY, DATABASE_URL и т.д.
```

### 3. Применить миграции

```bash
python manage.py migrate
```

### 4. Загрузить начальные данные

```bash
python manage.py setup_initial_data --superuser
```

Создаётся суперпользователь `admin` с паролем `admin123` — **смените пароль в продакшене!**

### 5. Запустить сервер разработки

```bash
python manage.py runserver
```

Приложение доступно по адресу: http://localhost:8000

Административная панель: http://localhost:8000/admin/

## Структура проекта

```
techcards/
├── apps/
│   ├── accounts/   — Пользователи, роли, личный кабинет
│   ├── core/       — Главная страница, контакты
│   ├── standards/  — Нормативные документы и методы НК
│   ├── cards/      — Разработка и хранение техкарт
│   ├── quality/    — Оценка качества сварных соединений
│   └── payments/   — Тарифы и платёжная система (ЮKassa)
├── ndt_data/       — Данные нормативных документов (расчётные модули)
│   ├── gost_7512.py
│   ├── rd_03_606_03.py
│   ├── gost_r_iso_17637.py
│   ├── gost_r_iso_3452.py
│   ├── gost_r_52005.py
│   └── np_105_18.py
├── card_templates/ — Шаблоны техкарт (DOCX-файлы)
├── templates/      — HTML-шаблоны
├── static/         — CSS, JS, изображения
└── config/         — Настройки Django
```

## Добавление нового нормативного документа

1. Создайте файл `ndt_data/<ваш_документ>.py`, наследуя `BaseNDTData`:
   ```python
   from ndt_data.base import BaseNDTData, FieldDefinition, DefectCriterion
   
   class MyDocData(BaseNDTData):
       DOCUMENT_CODE = "ГОСТ XXXXX"
       DOCUMENT_NAME = "Полное наименование"
       METHOD_CODE = "RT"
       
       def get_card_fields(self): ...
       def generate_card_data(self, input_data): ...
       def get_quality_criteria(self): ...
       def evaluate_defect(self, defect): ...
   ```

2. Добавьте запись в `ndt_data/registry.py`

3. Выполните `python manage.py setup_initial_data`

## Тарифные планы

| Кол-во техкарт | Цена |
|---|---|
| 1 | 300 руб. |
| 2 | 500 руб. |
| 3 | 600 руб. |
| 5 | 800 руб. |
| 10 | 1500 руб. |

Первая техкарта по каждому нормативному документу — **бесплатно**.

## Запуск тестов

```bash
python manage.py test apps
```

## Настройка ЮKassa

В файле `.env` укажите:
```
YOOKASSA_SHOP_ID=ваш-идентификатор-магазина
YOOKASSA_SECRET_KEY=ваш-секретный-ключ
```

URL для webhook: `https://ваш-домен.ru/payments/webhook/yookassa/`

## Деплой в продакшене

- Установите `DEBUG=False` в `.env`
- Настройте PostgreSQL (`DATABASE_URL`)
- Соберите статику: `python manage.py collectstatic`
- Используйте Gunicorn + Nginx
- Настройте HTTPS/SSL
