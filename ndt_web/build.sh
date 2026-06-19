#!/usr/bin/env bash
# Скрипт сборки для Render.com
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py init_data
