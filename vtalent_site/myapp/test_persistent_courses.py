from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Announcement, Batch, Course


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

    def test_invalid_batch_add_shows_error_and_does_not_save(self):
        response = self.client.post(reverse('batch_add'), {
            'course': '',
            'name': 'Invalid batch',
            'month': 9,
            'year': 2026,
        }, follow=True)

        self.assertContains(response, 'Batch was not saved.')
        self.assertFalse(Batch.objects.filter(name='Invalid batch').exists())

    def test_invalid_announcement_add_shows_error_and_does_not_save(self):
        response = self.client.post(reverse('announcement_add'), {
            'message': '',
            'is_active': 'on',
        }, follow=True)

        self.assertContains(response, 'Announcement was not published.')
        self.assertFalse(Announcement.objects.exists())

    def test_hidden_courses_and_batches_remain_listed_until_deleted(self):
        course = Course.objects.create(
            title='Always listed course',
            is_published=False,
        )
        batch = Batch.objects.create(
            course=course,
            name='Always listed batch',
            year=2026,
            google_form_url='https://forms.gle/persistent',
            is_visible=False,
            registrations_open=False,
        )

        for url in (reverse('home'), reverse('courses'), reverse('registration')):
            response = self.client.get(url)
            self.assertContains(response, course.title)
            self.assertContains(response, batch.name)
            self.assertContains(response, batch.google_form_url)

        course.delete()
        self.assertFalse(Batch.objects.filter(pk=batch.pk).exists())
        self.assertNotContains(self.client.get(reverse('courses')), course.title)

    def test_inactive_announcements_remain_on_public_pages_until_deleted(self):
        notice = Announcement.objects.create(
            message='Keep this notice visible',
            is_active=False,
        )

        for url in (reverse('home'), reverse('courses')):
            self.assertContains(self.client.get(url), notice.message)

        notice.delete()
        self.assertNotContains(self.client.get(reverse('home')), notice.message)
