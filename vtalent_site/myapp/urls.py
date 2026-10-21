from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('courses/', views.courses, name='courses'),
    path('registration/', views.registration, name='registration'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('admin-login/', views.staff_login, name='staff_login'),
    path('admin/logout/', views.staff_logout, name='staff_logout'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/course/add/', views.admin_course_add, name='admin_course_add'),
    path('course/add/', views.course_add, name='course_add'),
    path('course/<int:pk>/edit/', views.course_edit, name='course_edit'),
    path('course/<int:pk>/delete/', views.course_delete, name='course_delete'),
    path('batch/add/', views.batch_add, name='batch_add'),
    path('batch/<int:pk>/edit/', views.batch_edit, name='batch_edit'),
    path('batch/<int:pk>/registrations/', views.batch_registration_toggle, name='batch_registration_toggle'),
    path('batch/<int:pk>/delete/', views.batch_delete, name='batch_delete'),
    path('register/<int:batch_id>/', views.register_batch, name='register_batch'),
    path('announcement/add/', views.announcement_add, name='announcement_add'),
    path('announcement/<int:pk>/edit/', views.announcement_edit, name='announcement_edit'),
    path('announcement/<int:pk>/toggle/', views.announcement_toggle, name='announcement_toggle'),
    path('announcement/<int:pk>/delete/', views.announcement_delete, name='announcement_delete'),
]