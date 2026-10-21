from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Announcement, Batch, Course


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'category', 'description', 'duration', 'syllabus', 'display_order', 'is_published']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'duration': forms.TextInput(attrs={'class': 'form-control'}),
            'syllabus': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class CourseCreationForm(forms.Form):
    title = forms.CharField(
        max_length=200,
        label='Course title',
        widget=forms.TextInput(attrs={
            'class': 'course-input',
            'placeholder': 'e.g. Salesforce Development',
            'autocomplete': 'off',
        }),
    )
    category = forms.CharField(
        max_length=100,
        label='Category',
        widget=forms.TextInput(attrs={
            'class': 'course-input',
            'placeholder': 'e.g. Cloud CRM',
            'autocomplete': 'off',
        }),
    )
    batch_name = forms.CharField(
        max_length=200,
        label='Batch name',
        widget=forms.TextInput(attrs={
            'class': 'course-input',
            'placeholder': 'e.g. August Batch',
            'autocomplete': 'off',
        }),
    )
    duration = forms.CharField(
        max_length=100,
        label='Duration',
        widget=forms.TextInput(attrs={
            'class': 'course-input',
            'placeholder': 'e.g. 4 Months',
            'autocomplete': 'off',
        }),
    )
    google_form_link = forms.URLField(
        required=False,
        label='Google Form link',
        widget=forms.URLInput(attrs={
            'class': 'course-input',
            'placeholder': 'https://forms.gle/...',
            'inputmode': 'url',
        }),
    )
    syllabus = forms.CharField(
        required=False,
        label='Syllabus (one topic per line)',
        initial='Core concepts\nAdvanced topics\nReal-time project',
        widget=forms.Textarea(attrs={
            'class': 'course-input course-syllabus',
            'rows': 4,
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['aria-describedby'] = f'id_{field_name}_errors'


class BatchForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = ['course', 'name', 'month', 'year', 'duration', 'google_form_url', 'is_visible']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'month': forms.Select(attrs={'class': 'form-control'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'duration': forms.TextInput(attrs={'class': 'form-control'}),
            'google_form_url': forms.URLInput(attrs={'class': 'form-control'}),
        }


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['message', 'is_active']
        widgets = {
            'message': forms.TextInput(attrs={'class': 'form-control'}),
        }


def get_public_courses():
    return Course.objects.filter(is_published=True).order_by('display_order', 'title')


def get_active_announcements():
    return Announcement.objects.filter(is_active=True).order_by('-created_at')


def home(request):
    courses = get_public_courses().prefetch_related('batches')
    open_batches = Batch.objects.filter(
        registrations_open=True,
        is_visible=True,
        google_form_url__gt='',
    ).select_related('course').order_by('course__display_order', 'year', 'month')
    context = {
        'courses': courses,
        'open_batches': open_batches,
        'open_batch_count': open_batches.count(),
        'announcements': get_active_announcements(),
    }
    return render(request, 'home.html', context)


def courses(request):
    courses = get_public_courses().prefetch_related('batches')
    return render(request, 'courses.html', {'courses': courses, 'announcements': get_active_announcements()})


def registration(request):
    courses = get_public_courses().prefetch_related('batches')
    selected_course_id = request.GET.get('course')
    return render(request, 'registration.html', {
        'courses': courses,
        'selected_course_id': selected_course_id,
        'announcements': get_active_announcements(),
    })


def about(request):
    return render(request, 'about.html', {'announcements': get_active_announcements()})


def contact(request):
    return render(request, 'contact.html', {'announcements': get_active_announcements()})


def staff_login(request):
    if request.user.is_authenticated:
        return redirect('admin_dashboard')

    error = None
    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password') or ''

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('admin_dashboard')

        error = 'Invalid username or password.'

    return render(request, 'admin_login.html', {'error': error, 'announcements': get_active_announcements()})


@login_required(login_url='staff_login')
@user_passes_test(lambda user: user.is_staff, login_url='staff_login')
def admin_dashboard(request):
    courses = Course.objects.all().prefetch_related('batches').order_by('display_order', 'title')
    all_announcements = Announcement.objects.order_by('-created_at')
    return render(request, 'admin.html', {
        'courses': courses,
        'all_announcements': all_announcements,
        'batch_form': BatchForm(),
        'announcement_form': AnnouncementForm(),
        'announcements': get_active_announcements(),
    })


@login_required(login_url='staff_login')
@user_passes_test(lambda user: user.is_staff, login_url='staff_login')
def admin_course_add(request):
    is_submitted = request.method == 'POST'
    form = CourseCreationForm(request.POST if is_submitted else None)
    if is_submitted:
        if form.is_valid():
            topics = [topic.strip() for topic in form.cleaned_data['syllabus'].splitlines() if topic.strip()]
            today = timezone.localdate()
            with transaction.atomic():
                course = Course.objects.create(
                    title=form.cleaned_data['title'],
                    category=form.cleaned_data['category'],
                    duration=form.cleaned_data['duration'],
                    syllabus='\n'.join(topics),
                )
                Batch.objects.create(
                    course=course,
                    name=form.cleaned_data['batch_name'],
                    month=today.month,
                    year=today.year,
                    duration=form.cleaned_data['duration'],
                    google_form_url=form.cleaned_data['google_form_link'],
                    registrations_open=False,
                )
            messages.success(request, f'{course.title} was added successfully. Registrations are closed.')
            return redirect('admin_course_add')

        for field_name, field in form.fields.items():
            if form.errors.get(field_name):
                field.widget.attrs['aria-invalid'] = 'true'

    return render(request, 'course_add.html', {
        'form': form,
        'announcements': [],
    })


@login_required(login_url='staff_login')
@user_passes_test(lambda user: user.is_staff, login_url='staff_login')
def course_add(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course added successfully.')
    return redirect('admin_dashboard')


@login_required(login_url='staff_login')
@user_passes_test(lambda user: user.is_staff, login_url='staff_login')
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course updated successfully.')
    return redirect('admin_dashboard')


@login_required(login_url='staff_login')
@user_passes_test(lambda user: user.is_staff, login_url='staff_login')
@require_POST
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    course.delete()
    messages.success(request, 'Course deleted.')
    return redirect('admin_dashboard')


@login_required(login_url='staff_login')
@user_passes_test(lambda user: user.is_staff, login_url='staff_login')
def batch_add(request):
    if request.method == 'POST':
        form = BatchForm(request.POST)
        if form.is_valid():
            batch = form.save(commit=False)
            batch.registrations_open = False
            batch.save()
            messages.success(request, 'Batch added successfully. Open registrations when its form link is ready.')
    return redirect('admin_dashboard')


@login_required(login_url='staff_login')
@user_passes_test(lambda user: user.is_staff, login_url='staff_login')
def batch_edit(request, pk):
    batch = get_object_or_404(Batch, pk=pk)
    if request.method == 'POST':
        saved_google_form_url = batch.google_form_url
        form = BatchForm(request.POST, instance=batch)
        if form.is_valid():
            updated_batch = form.save(commit=False)
            if saved_google_form_url and not form.cleaned_data['google_form_url']:
                updated_batch.google_form_url = saved_google_form_url
                messages.success(
                    request,
                    'Batch updated. The existing registration link was kept; replace it or delete the batch to remove it.',
                )
            else:
                messages.success(request, 'Batch updated successfully.')
            updated_batch.save()
    return redirect('admin_dashboard')


@login_required(login_url='staff_login')
@user_passes_test(lambda user: user.is_staff, login_url='staff_login')
@require_POST
def batch_registration_toggle(request, pk):
    batch = get_object_or_404(Batch, pk=pk)
    action = request.POST.get('action')

    if action == 'open':
        if not batch.google_form_url:
            messages.error(request, 'Add a Google Form link before opening registrations.')
        elif not batch.registrations_open:
            batch.registrations_open = True
            batch.save(update_fields=['registrations_open', 'updated_at'])
            messages.success(request, f'Registrations opened for {batch.name}.')
    elif action == 'close':
        if batch.registrations_open:
            batch.registrations_open = False
            batch.save(update_fields=['registrations_open', 'updated_at'])
            messages.success(request, f'Registrations closed for {batch.name}.')
    else:
        messages.error(request, 'Choose whether to open or close registrations.')

    return redirect('admin_dashboard')


@login_required(login_url='staff_login')
@user_passes_test(lambda user: user.is_staff, login_url='staff_login')
@require_POST
def batch_delete(request, pk):
    batch = get_object_or_404(Batch, pk=pk)
    batch.delete()
    messages.success(request, 'Batch deleted.')
    return redirect('admin_dashboard')


@login_required(login_url='staff_login')
@user_passes_test(lambda user: user.is_staff, login_url='staff_login')
@require_POST
def announcement_add(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Announcement published.')
    return redirect('admin_dashboard')


@login_required(login_url='staff_login')
@user_passes_test(lambda user: user.is_staff, login_url='staff_login')
@require_POST
def announcement_edit(request, pk):
    notice = get_object_or_404(Announcement, pk=pk)
    form = AnnouncementForm(
        {
            'message': request.POST.get('message', ''),
            'is_active': notice.is_active,
        },
        instance=notice,
    )
    if form.is_valid():
        form.save()
        messages.success(request, 'Announcement updated.')
    else:
        messages.error(request, 'Enter a valid announcement.')
    return redirect('admin_dashboard')


@login_required(login_url='staff_login')
@user_passes_test(lambda user: user.is_staff, login_url='staff_login')
@require_POST
def announcement_toggle(request, pk):
    notice = get_object_or_404(Announcement, pk=pk)
    notice.is_active = not notice.is_active
    notice.save()
    messages.success(request, 'Announcement updated.')
    return redirect('admin_dashboard')


@login_required(login_url='staff_login')
@user_passes_test(lambda user: user.is_staff, login_url='staff_login')
@require_POST
def announcement_delete(request, pk):
    notice = get_object_or_404(Announcement, pk=pk)
    notice.delete()
    messages.success(request, 'Announcement deleted.')
    return redirect('admin_dashboard')


def staff_logout(request):
    logout(request)
    return redirect('home')


def register_batch(request, batch_id):
    batch = get_object_or_404(Batch, pk=batch_id)
    if batch.google_form_url:
        return redirect(batch.google_form_url)
    return redirect('registration')
