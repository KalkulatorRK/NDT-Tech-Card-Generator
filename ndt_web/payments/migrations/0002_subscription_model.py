"""Переход с пакетов кредитов на подписки с лимитом генераций."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_tariff_to_subscription(apps, schema_editor):
    SubscriptionPlan = apps.get_model('payments', 'SubscriptionPlan')
    for plan in SubscriptionPlan.objects.all():
        if not plan.name:
            plan.name = f'Подписка {plan.generation_limit} ген.'
        if not plan.duration_days:
            plan.duration_days = 30
        plan.save(update_fields=['name', 'duration_days'])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='TariffPlan',
            new_name='SubscriptionPlan',
        ),
        migrations.RenameField(
            model_name='subscriptionplan',
            old_name='cards_count',
            new_name='generation_limit',
        ),
        migrations.AddField(
            model_name='subscriptionplan',
            name='name',
            field=models.CharField(default='', max_length=100, verbose_name='Название', blank=True),
        ),
        migrations.AddField(
            model_name='subscriptionplan',
            name='duration_days',
            field=models.PositiveIntegerField(
                default=30,
                help_text='Например, 30 — подписка на 1 месяц',
                verbose_name='Длительность, дней',
            ),
        ),
        migrations.AlterModelOptions(
            name='subscriptionplan',
            options={
                'ordering': ['price'],
                'verbose_name': 'План подписки',
                'verbose_name_plural': 'Планы подписки',
            },
        ),
        migrations.RenameField(
            model_name='payment',
            old_name='tariff',
            new_name='plan',
        ),
        migrations.CreateModel(
            name='UserSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[('active', 'Активна'), ('expired', 'Истекла'), ('canceled', 'Отменена')],
                    default='active', max_length=20, verbose_name='Статус',
                )),
                ('period_start', models.DateTimeField(verbose_name='Начало периода')),
                ('period_end', models.DateTimeField(verbose_name='Окончание периода')),
                ('generations_used', models.PositiveIntegerField(
                    default=0, verbose_name='Использовано генераций в периоде',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создана')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('plan', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='user_subscriptions',
                    to='payments.subscriptionplan',
                    verbose_name='План подписки',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='subscriptions',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Пользователь',
                )),
            ],
            options={
                'verbose_name': 'Подписка пользователя',
                'verbose_name_plural': 'Подписки пользователей',
                'ordering': ['-period_end'],
            },
        ),
        migrations.AddField(
            model_name='payment',
            name='subscription',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='payments',
                to='payments.usersubscription',
                verbose_name='Активированная подписка',
            ),
        ),
        migrations.RunPython(migrate_tariff_to_subscription, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='subscriptionplan',
            name='name',
            field=models.CharField(max_length=100, verbose_name='Название'),
        ),
    ]
