from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import migrations, models
import django.db.models.deletion


def disable_legacy_admin_password(apps, schema_editor):
    app_label, model_name = settings.AUTH_USER_MODEL.split('.')
    User = apps.get_model(app_label, model_name)
    database = schema_editor.connection.alias
    for user in User.objects.using(database).filter(username='admin'):
        if check_password('admin123', user.password):
            user.password = make_password(None)
            user.save(using=database, update_fields=['password'])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('myapp', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminPasswordResetOTP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code_hash', models.CharField(max_length=128)),
                ('created_at', models.DateTimeField()),
                ('expires_at', models.DateTimeField()),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='admin_password_reset_otp',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
        migrations.RunPython(
            disable_legacy_admin_password,
            migrations.RunPython.noop,
        ),
    ]
