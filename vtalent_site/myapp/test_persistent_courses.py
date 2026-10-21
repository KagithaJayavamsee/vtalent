from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Batch, Course


class PersistentCourseTests(TestCase):
    def setUp(self):
        self.staff_user = get_user_model().objects.create_user(
            username='persistent-course-manager',
            password='test-password',
            is_staff=True,
        )
        self.client.force_login(self.staff_user)

    def test_default_courses_are_created_by_migrations(self):
        titles = set(Course.objects.values_list('title', flat=True))

        self.assertIn('Java Full Stack Development, AI Integration & AWS Cloud', titles)
        self.assertIn('Python Full Stack Development, AI/ML & AWS Cloud', titles)

    def test_batch_edit_preserves_existing_registration_link_if_blank(self):
        course = Course.objects.create(title='Course for link test')
        batch = Batch.objects.create(
            course=course,
            name='September Batch',
            year=2026,
            google_form_url='https://forms.gle/example',
        )

        response = self.client.post(reverse('batch_edit', args=[batch.pk]), {
            'course': course.pk,
            'name': batch.name,
            'month': 9,
            'year': batch.year,
            'duration': '',
            'google_form_url': '',
            'is_visible': 'on',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        batch.refresh_from_db()
        self.assertEqual(batch.google_form_url, 'https://forms.gle/example')
