"""
Настройки Django для приложения автоматизации НК «НК-Карта».

Документация: https://docs.djangoproject.com/en/4.2/topics/settings/
"""

import os
import dj_database_url
from pathlib import Path
from decouple import config, Csv

# Корневая директория проекта
BASE_DIR = Path(__file__).resolve().parent.parent

# ------------------------------------------------------------------
# Безопасность
# ------------------------------------------------------------------
SECRET_KEY = config('SECRET_KEY', default='django-insecure-замените-в-продакшн')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1,.railway.app,.onrender.com,.vercel.app',
    cast=Csv(),
)

# ------------------------------------------------------------------
# Приложения
# ------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Сторонние библиотеки
    'crispy_forms',
    'crispy_bootstrap5',
    'django_recaptcha',

    # Приложения проекта
    'accounts.apps.AccountsConfig',
    'techcards.apps.TechcardsConfig',
    'quality.apps.QualityConfig',
    'payments.apps.PaymentsConfig',
    'normative.apps.NormativeConfig',
    'forum.apps.ForumConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # Раздача статики
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ndt_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ndt_project.wsgi.application'

# ------------------------------------------------------------------
# База данных
# При наличии переменной DATABASE_URL (Railway, Render, Heroku) —
# используется PostgreSQL. Иначе — локальный SQLite.
# ------------------------------------------------------------------
DATABASE_URL = config('DATABASE_URL', default=None)

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            engine='django.db.backends.postgresql',
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
}

# ------------------------------------------------------------------
# Валидация паролей
# ------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ------------------------------------------------------------------
# Локализация
# ------------------------------------------------------------------
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------------
# Статические и медиа файлы
# ------------------------------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Django 5.x: настройка хранилища через STORAGES (вместо STATICFILES_STORAGE)
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ------------------------------------------------------------------
# Кастомный пользователь
# ------------------------------------------------------------------
AUTH_USER_MODEL = 'accounts.CustomUser'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ------------------------------------------------------------------
# Кэш (для django-ratelimit)
# ------------------------------------------------------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'ndt-cache',
    }
}

# ------------------------------------------------------------------
# reCAPTCHA v3 (защита формы регистрации от ботов)
# ------------------------------------------------------------------
RECAPTCHA_PUBLIC_KEY = config('RECAPTCHA_PUBLIC_KEY', default='')
RECAPTCHA_PRIVATE_KEY = config('RECAPTCHA_PRIVATE_KEY', default='')
RECAPTCHA_REQUIRED_SCORE = config('RECAPTCHA_REQUIRED_SCORE', default=0.5, cast=float)

# ------------------------------------------------------------------
# Лимиты регистрации
# ------------------------------------------------------------------
REGISTRATION_RATE_LIMIT = '5/h'

# ------------------------------------------------------------------
# Crispy Forms (Bootstrap 5)
# ------------------------------------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# ------------------------------------------------------------------
# Аутентификация
# ------------------------------------------------------------------
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/cabinet/'
LOGOUT_REDIRECT_URL = '/'

# ------------------------------------------------------------------
# Сессии
# ------------------------------------------------------------------
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14   # 2 недели
SESSION_SAVE_EVERY_REQUEST = True

# ------------------------------------------------------------------
# Безопасность
# ------------------------------------------------------------------

# Render, Railway и другие PaaS-платформы завершают SSL на своём прокси.
# Django видит трафик как HTTP, поэтому SSL_REDIRECT и SECURE_COOKIES
# здесь НЕ включаем — это ломает CSRF и сессии.
# Вместо этого сообщаем Django, что прокси обрабатывает HTTPS.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    # SECURE_SSL_REDIRECT — не включать, Render сам редиректит HTTP→HTTPS
    # SESSION_COOKIE_SECURE и CSRF_COOKIE_SECURE временно отключены
    # до выяснения причины 500-ошибки
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# CSRF: доверенные источники (обязательно для работы форм и админки на HTTPS)
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='https://*.onrender.com,https://*.railway.app',
    cast=Csv(),
)

# ------------------------------------------------------------------
# Email (подтверждение регистрации, уведомления)
# ------------------------------------------------------------------
EMAIL_HOST = config('EMAIL_HOST', default='smtp.yandex.ru')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=10, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# Нельзя одновременно SSL (465) и STARTTLS (587)
if EMAIL_PORT == 465:
    EMAIL_USE_SSL = True
    EMAIL_USE_TLS = False
elif EMAIL_PORT == 587:
    EMAIL_USE_TLS = True
    EMAIL_USE_SSL = False

# Адрес «От кого» в письмах пользователям (должен совпадать с EMAIL_HOST_USER для Yandex)
DEFAULT_FROM_EMAIL = config(
    'DEFAULT_FROM_EMAIL',
    default=EMAIL_HOST_USER or 'noreply@nk-karta.ru',
)
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# Если заданы SMTP-учётные данные — отправляем реальные письма, иначе — в консоль (dev)
if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = config(
        'EMAIL_BACKEND',
        default='django.core.mail.backends.smtp.EmailBackend',
    )
else:
    EMAIL_BACKEND = config(
        'EMAIL_BACKEND',
        default='django.core.mail.backends.console.EmailBackend',
    )

# ------------------------------------------------------------------
# ЮKassa (платёжная система)
# ------------------------------------------------------------------
YOOKASSA_SHOP_ID = config('YOOKASSA_SHOP_ID', default='')
YOOKASSA_SECRET_KEY = config('YOOKASSA_SECRET_KEY', default='')
SITE_URL = config('SITE_URL', default='http://localhost:8000')

# ------------------------------------------------------------------
# Гостевой доступ к оценке качества
# ------------------------------------------------------------------
GUEST_QUALITY_ASSESSMENTS_LIMIT = 3

# ------------------------------------------------------------------
# Лимиты бесплатных техкарт
# ------------------------------------------------------------------
FREE_TECHCARD_PER_DOCUMENT = 1   # 1 бесплатная карта по каждому документу
