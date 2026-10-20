from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core import serializers
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connections, transaction

from myapp.models import Announcement, Batch, Course


DEFAULT_COURSE_TITLES = (
    'Java Full Stack Development, AI Integration & AWS Cloud',
    'Python Full Stack Development, AI/ML & AWS Cloud',
)
DEFAULT_COURSES = (
    {
        'title': DEFAULT_COURSE_TITLES[0],
        'category': 'Java • Frontend • Backend • AI • Cloud',
        'syllabus': (
            'Frontend Development\n'
            'Core Java and Advanced Java\n'
            'Database Management with MySQL\n'
            'Spring Boot and REST APIs\n'
            'AI Integration in Applications\n'
            'AWS Cloud and Deployment'
        ),
        'display_order': 1,
    },
    {
        'title': DEFAULT_COURSE_TITLES[1],
        'category': 'Python • Frontend • Django • Machine Learning • Cloud',
        'syllabus': (
            'Frontend Development\n'
            'Core Python and Advanced Python\n'
            'Database Management with MySQL\n'
            'Django and REST APIs\n'
            'Artificial Intelligence and Machine Learning\n'
            'AWS Cloud and Deployment'
        ),
        'display_order': 2,
    },
)


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

        target_has_data = (
            Course.objects.using('default').exclude(title__in=DEFAULT_COURSE_TITLES).exists()
            or Batch.objects.using('default').exists()
            or Announcement.objects.using('default').exists()
        )
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
                if any(isinstance(item.object, Course) for item in objects):
                    Course.objects.using('default').filter(
                        title__in=DEFAULT_COURSE_TITLES,
                    ).delete()
                for item in objects:
                    item.save(using='default')
                for item in objects:
                    item.save_deferred_fields(using='default')
                self._ensure_default_courses()

        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text('Legacy records copied successfully.\n', encoding='utf-8')
        self.stdout.write(self.style.SUCCESS('Legacy courses, batches, notes, and admin accounts copied.'))

    @staticmethod
    def _ensure_default_courses():
        for course_data in DEFAULT_COURSES:
            Course.objects.using('default').get_or_create(
                title=course_data['title'],
                defaults={
                    'category': course_data['category'],
                    'syllabus': course_data['syllabus'],
                    'display_order': course_data['display_order'],
                    'is_published': True,
                },
            )

    @staticmethod
    def _users_exist(database):
        from django.contrib.auth import get_user_model

        return get_user_model().objects.using(database).exists()
