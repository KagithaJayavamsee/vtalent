from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core import serializers
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connections, transaction

from myapp.models import Announcement, Batch, Course


class Command(BaseCommand):
    help = 'Copy existing courses, batches, notes, and admin accounts to persistent SQLite.'

    def handle(self, *args, **options):
        if 'legacy' not in connections:
            self.stdout.write('No legacy database is configured; skipping the one-time data copy.')
            return

        marker = Path(settings.DATABASES['default']['NAME']).with_suffix('.legacy-data-copied')
        if marker.exists():
            self.stdout.write('Legacy data was already copied to this database.')
            return

        models = (Course, Batch, Announcement)
        target_has_data = any(model.objects.using('default').exists() for model in models)
        target_has_users = (
            connections['default'].introspection.table_names()
            and self._users_exist('default')
        )
        if target_has_data or target_has_users:
            raise CommandError(
                'The SQLite database already contains courses, batches, notes, or admin accounts. '
                'Refusing to overwrite existing data during the legacy copy.'
            )

        fixture = StringIO()
        call_command(
            'dumpdata',
            'auth.User',
            'auth.Group',
            'myapp.Course',
            'myapp.Batch',
            'myapp.Announcement',
            database='legacy',
            natural_foreign=True,
            stdout=fixture,
            verbosity=0,
        )
        fixture.seek(0)
        if fixture.getvalue().strip():
            objects = list(serializers.deserialize(
                'json',
                fixture.getvalue(),
                using='default',
                handle_forward_references=True,
            ))
            with transaction.atomic(using='default'):
                for item in objects:
                    item.save(using='default')
                for item in objects:
                    item.save_deferred_fields(using='default')

        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text('Legacy records copied successfully.\n', encoding='utf-8')
        self.stdout.write(self.style.SUCCESS('Legacy courses, batches, notes, and admin accounts copied.'))

    @staticmethod
    def _users_exist(database):
        from django.contrib.auth import get_user_model

        return get_user_model().objects.using(database).exists()
