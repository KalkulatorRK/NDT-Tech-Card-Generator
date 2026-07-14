"""Расширение section_label до 200 (длинные метки с НД+пункт)."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_consultant', '0002_enable_pgvector'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documentchunk',
            name='section_label',
            field=models.CharField(max_length=200, blank=True, verbose_name='Пункт/раздел'),
        ),
    ]
