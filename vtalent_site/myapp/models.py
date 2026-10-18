from django.db import models


class Course(models.Model):
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    duration = models.CharField(max_length=100, blank=True)
    syllabus = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'title']

    def __str__(self):
        return self.title

    @property
    def syllabus_items(self):
        if not self.syllabus:
            return []
        return [item.strip() for item in self.syllabus.splitlines() if item.strip()]


class Batch(models.Model):
    MONTH_CHOICES = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December'),
    ]

    course = models.ForeignKey(Course, related_name='batches', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    month = models.PositiveSmallIntegerField(choices=MONTH_CHOICES, default=1)
    year = models.PositiveIntegerField(default=2025)
    duration = models.CharField(max_length=100, blank=True)
    google_form_url = models.URLField(blank=True)
    registrations_open = models.BooleanField(default=True)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['year', 'month', 'name']

    def __str__(self):
        return f'{self.course.title} - {self.name}'

    @property
    def month_year(self):
        return f'{self.get_month_display()} {self.year}'

    @property
    def can_register(self):
        return self.registrations_open and bool(self.google_form_url)

    @property
    def is_visible_public(self):
        return self.is_visible


class Announcement(models.Model):
    message = models.CharField(max_length=250)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.message
