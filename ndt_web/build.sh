#!/usr/bin/env bash
# Скрипт сборки для Render.com
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
# init_data запускается только если нет суперпользователя
python manage.py init_data || echo "init_data: пропускаем (данные уже загружены)"
