# Generated manually for email verification feature

from django.db import migrations, models


def verify_existing_users(apps, schema_editor):
    """Существующие пользователи считаются с подтверждённым email."""
    User = apps.get_model('accounts', 'CustomUser')
    User.objects.all().update(email_verified=True)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='email_verified',
            field=models.BooleanField(
                default=False,
                help_text='Пользователь перешёл по ссылке из письма после регистрации',
                verbose_name='Email подтверждён',
            ),
        ),
        migrations.RunPython(verify_existing_users, migrations.RunPython.noop),
    ]
