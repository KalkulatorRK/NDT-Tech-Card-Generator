#!/usr/bin/env bash
# Скрипт сборки для Render.com
set -o errexit

PYTHON="${PYTHON:-python3}"

pip install -r requirements.txt
"$PYTHON" manage.py collectstatic --noinput
"$PYTHON" manage.py migrate --noinput
# init_data идемпотентен: не пересоздаёт существующие данные
"$PYTHON" manage.py init_data || echo "init_data: пропускаем (данные уже загружены)"
