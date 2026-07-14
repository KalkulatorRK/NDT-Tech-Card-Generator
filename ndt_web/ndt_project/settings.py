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
    'anymail',

    # Приложения проекта
    'accounts.apps.AccountsConfig',
    'techcards.apps.TechcardsConfig',
    'quality.apps.QualityConfig',
    'payments.apps.PaymentsConfig',
    'normative.apps.NormativeConfig',
    'forum.apps.ForumConfig',
    'ai_consultant.apps.AiConsultantConfig',
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
    _db_config = dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=0,
        engine='django.db.backends.postgresql',
    )
    _db_config.setdefault('OPTIONS', {})
    if _db_config['OPTIONS'].get('sslmode') is None:
        _db_config['OPTIONS']['sslmode'] = 'require'
    DATABASES = {'default': _db_config}
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
from accounts.email_config import resolve_smtp_settings
from accounts.email_settings import resolve_email_backend

RESEND_API_KEY = config('RESEND_API_KEY', default='').strip()
UNISENDER_GO_API_KEY = config('UNISENDER_GO_API_KEY', default='').strip()
UNISENDER_GO_API_URL = config(
    'UNISENDER_GO_API_URL',
    default='https://go1.unisender.ru/ru/transactional/api/v1/',
).strip()
BREVO_SMTP_KEY = config('BREVO_SMTP_KEY', default='').strip()
BREVO_LOGIN = config('BREVO_LOGIN', default='').strip()

_smtp = resolve_smtp_settings(
    brevo_smtp_key=BREVO_SMTP_KEY,
    brevo_login=BREVO_LOGIN,
    email_host=config('EMAIL_HOST', default=''),
    email_port=config('EMAIL_PORT', default=587, cast=int),
    email_use_tls=config('EMAIL_USE_TLS', default=True, cast=bool),
    email_use_ssl=config('EMAIL_USE_SSL', default=False, cast=bool),
    email_host_user=config('EMAIL_HOST_USER', default=''),
    email_host_password=config('EMAIL_HOST_PASSWORD', default=''),
)
EMAIL_HOST = _smtp['EMAIL_HOST']
EMAIL_PORT = _smtp['EMAIL_PORT']
EMAIL_USE_TLS = _smtp['EMAIL_USE_TLS']
EMAIL_USE_SSL = _smtp['EMAIL_USE_SSL']
EMAIL_HOST_USER = _smtp['EMAIL_HOST_USER']
EMAIL_HOST_PASSWORD = _smtp['EMAIL_HOST_PASSWORD']
EMAIL_TIMEOUT = config('EMAIL_TIMEOUT', default=10, cast=int)

DEFAULT_FROM_EMAIL = config(
    'DEFAULT_FROM_EMAIL',
    default=EMAIL_HOST_USER or 'onboarding@resend.dev',
).strip()
SERVER_EMAIL = DEFAULT_FROM_EMAIL

_email_backend, _email_backend_warning = resolve_email_backend(
    unisender_go_api_key=UNISENDER_GO_API_KEY,
    resend_api_key=RESEND_API_KEY,
    email_host=EMAIL_HOST,
    email_host_user=EMAIL_HOST_USER,
    email_host_password=EMAIL_HOST_PASSWORD,
    explicit_backend=config('EMAIL_BACKEND', default=''),
)
EMAIL_BACKEND = _email_backend
if _email_backend_warning:
    import logging
    logging.getLogger('ndt_project.settings').warning(_email_backend_warning)

# Приоритет: Unisender Go (РФ) → Resend → Brevo/SMTP → консоль (dev)
if UNISENDER_GO_API_KEY:
    ANYMAIL = {
        'UNISENDER_GO_API_KEY': UNISENDER_GO_API_KEY,
        'UNISENDER_GO_API_URL': UNISENDER_GO_API_URL,
    }
elif RESEND_API_KEY:
    ANYMAIL = {
        'RESEND_API_KEY': RESEND_API_KEY,
    }

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
