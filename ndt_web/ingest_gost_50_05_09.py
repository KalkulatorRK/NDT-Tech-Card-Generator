"""Обёртка: python ingest_gost_50_05_09.py → manage.py ingest_gost_50_05_09."""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ndt_project.settings')

import django
django.setup()

from django.core.management import call_command

if __name__ == '__main__':
    call_command('ingest_gost_50_05_09')
