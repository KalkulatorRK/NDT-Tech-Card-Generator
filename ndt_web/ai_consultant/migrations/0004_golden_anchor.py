"""Добавление флага is_golden для эталонных якорей (golden answers).

Слой обратного инжиниринга: точные ответы на типовые вопросы
(эталонные пункты НД) помечаются is_golden=True и получают
приоритет в retrieval/orchestrator. Раздел 7 ТЗ (дополнение).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_consultant', '0003_widen_section_label'),
    ]

    operations = [
        migrations.AddField(
            model_name='documentchunk',
            name='is_golden',
            field=models.BooleanField(
                default=False,
                verbose_name='Эталонный якорь (golden answer)',
            ),
        ),
    ]
