from django.contrib import admin

from .models import Announcement, Batch, Course


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'duration', 'is_published', 'display_order')
    list_filter = ('is_published',)
    search_fields = ('title', 'category', 'description')


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('course', 'name', 'month_year', 'registrations_open', 'is_visible')
    list_filter = ('registrations_open', 'is_visible', 'course')
    search_fields = ('name', 'course__title')


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('message', 'is_active', 'created_at')
    list_filter = ('is_active',)
