from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import resolve, reverse

from .models import Batch, Course


class AdminUrlTests(SimpleTestCase):
    def test_dashboard_url_resolves_to_site_dashboard(self):
        self.assertEqual(resolve('/admin/dashboard/').view_name, 'admin_dashboard')

    def test_logout_url_resolves_to_site_logout(self):
        self.assertEqual(resolve('/admin/logout/').view_name, 'staff_logout')

    def test_course_creation_page_resolves_outside_django_admin_catch_all(self):
        self.assertEqual(resolve('/admin/course/add/').view_name, 'admin_course_add')


class StaffLoginTests(TestCase):
    def test_staff_user_can_sign_in_with_changed_password(self):
        staff_user = get_user_model().objects.create_user(
            username='admin',
            password='New-safe-password-9!',
            is_staff=True,
            is_superuser=True,
        )

        response = self.client.post(reverse('staff_login'), {
            'username': 'admin',
            'password': 'New-safe-password-9!',
        })

        self.assertRedirects(response, reverse('admin_dashboard'))
        self.assertEqual(int(self.client.session['_auth_user_id']), staff_user.pk)

    def test_old_default_password_does_not_reset_changed_admin_password(self):
        staff_user = get_user_model().objects.create_user(
            username='admin',
            password='New-safe-password-9!',
            is_staff=True,
            is_superuser=True,
        )

        response = self.client.post(reverse('staff_login'), {
            'username': 'admin',
            'password': 'admin123',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password.')
        staff_user.refresh_from_db()
        self.assertTrue(staff_user.check_password('New-safe-password-9!'))
        self.assertNotIn('_auth_user_id', self.client.session)


class AdminCourseCreationTests(TestCase):
    def setUp(self):
        self.staff_user = get_user_model().objects.create_user(
            username='course-manager',
            password='test-password',
            is_staff=True,
        )
        self.client.force_login(self.staff_user)
        self.url = reverse('admin_course_add')

    def test_course_creation_page_shows_example_syllabus(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add a New Course')
        self.assertContains(response, 'Core concepts')
        self.assertContains(response, 'https://forms.gle/...')

    def test_dashboard_links_to_course_creation_page(self):
        response = self.client.get(reverse('admin_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.url)
        self.assertContains(response, '+ Add New Course')

    def test_course_is_deleted_only_after_explicit_post(self):
        course = Course.objects.create(title='Salesforce Development')
        delete_url = reverse('course_delete', args=[course.pk])

        response = self.client.get(delete_url)

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Course.objects.filter(pk=course.pk).exists())

        response = self.client.post(delete_url)

        self.assertRedirects(response, reverse('admin_dashboard'))
        self.assertFalse(Course.objects.filter(pk=course.pk).exists())

    def test_default_courses_are_available(self):
        response = self.client.get(reverse('admin_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Java Full Stack Development, AI Integration &amp; AWS Cloud')
        self.assertContains(response, 'Python Full Stack Development, AI/ML &amp; AWS Cloud')

    def test_batch_edit_keeps_registration_link_when_blank(self):
        course = Course.objects.create(title='Salesforce Development')
        batch = Batch.objects.create(
            course=course,
            name='August Batch',
            year=2026,
            google_form_url='https://forms.gle/example',
        )

        response = self.client.post(reverse('batch_edit', args=[batch.pk]), {
            'course': course.pk,
            'name': 'September Batch',
            'month': 9,
            'year': 2026,
            'duration': '',
            'google_form_url': '',
            'is_visible': 'on',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        batch.refresh_from_db()
        self.assertEqual(batch.name, 'September Batch')
        self.assertEqual(batch.year, 2026)
        self.assertEqual(batch.google_form_url, 'https://forms.gle/example')
        self.assertContains(response, 'The existing registration link was kept')

        response = self.client.post(reverse('batch_edit', args=[batch.pk]), {
            'course': course.pk,
            'name': 'September Batch',
            'month': 9,
            'year': 2026,
            'duration': '',
            'google_form_url': 'https://forms.gle/updated',
            'is_visible': 'on',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        batch.refresh_from_db()
        self.assertEqual(batch.google_form_url, 'https://forms.gle/updated')

    def test_valid_submission_creates_course_and_closed_batch(self):
        response = self.client.post(self.url, {
            'title': 'Salesforce Development',
            'category': 'Cloud CRM',
            'batch_name': 'August Batch',
            'duration': '6 Months',
            'google_form_link': 'https://forms.gle/example',
            'syllabus': 'Core concepts\n\n Advanced topics \nReal-time project',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Salesforce Development was added successfully')
        self.assertEqual(response.redirect_chain[-1][0], reverse('admin_dashboard'))
        self.assertContains(response, '+ Add New Course')
        course = Course.objects.get(title='Salesforce Development')
        batch = Batch.objects.get(course=course)
        self.assertEqual(course.syllabus_items, ['Core concepts', 'Advanced topics', 'Real-time project'])
        self.assertEqual(batch.name, 'August Batch')
        self.assertEqual(batch.duration, '6 Months')
        self.assertEqual(batch.google_form_url, 'https://forms.gle/example')
        self.assertFalse(batch.registrations_open)

    def test_registration_controls_open_and_close_batch(self):
        course = Course.objects.create(title='Salesforce Development')
        batch = Batch.objects.create(
            course=course,
            name='August Batch',
            google_form_url='https://forms.gle/example',
            registrations_open=False,
        )
        url = reverse('batch_registration_toggle', args=[batch.pk])

        response = self.client.post(url, {'action': 'open'}, follow=True)
        batch.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(batch.registrations_open)
        self.assertContains(response, 'Registrations opened for August Batch.')

        response = self.client.post(url, {'action': 'close'}, follow=True)
        batch.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(batch.registrations_open)
        self.assertContains(response, 'Registrations closed for August Batch.')

    def test_registrations_cannot_open_without_google_form_link(self):
        course = Course.objects.create(title='Salesforce Development')
        batch = Batch.objects.create(
            course=course,
            name='August Batch',
            registrations_open=False,
        )

        response = self.client.post(
            reverse('batch_registration_toggle', args=[batch.pk]),
            {'action': 'open'},
            follow=True,
        )

        batch.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(batch.registrations_open)
        self.assertContains(response, 'Add a Google Form link before opening registrations.')

    def test_new_batch_starts_with_registrations_closed(self):
        course = Course.objects.create(title='Salesforce Development')

        response = self.client.post(reverse('batch_add'), {
            'course': course.pk,
            'name': 'August Batch',
            'month': 8,
            'year': 2026,
            'duration': '4 Months',
            'google_form_url': 'https://forms.gle/example',
            'is_visible': 'on',
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        batch = Batch.objects.get(course=course)
        self.assertFalse(batch.registrations_open)

    def test_invalid_required_fields_and_google_form_url_are_reported(self):
        response = self.client.post(self.url, {
            'title': '',
            'category': 'Cloud CRM',
            'batch_name': 'August Batch',
            'duration': '4 Months',
            'google_form_link': 'not-a-url',
            'syllabus': 'Core concepts',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.')
        self.assertContains(response, 'Enter a valid URL.')
        self.assertFalse(Course.objects.filter(title='Salesforce Development').exists())
