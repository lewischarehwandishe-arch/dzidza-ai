from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    path('subjects/', views.subject_list, name='subject_list'),
    path('subjects/<int:pk>/delete/', views.subject_delete, name='subject_delete'),

    path('timetable/', views.timetable_view, name='timetable'),
    path('timetable/add/', views.timetable_add, name='timetable_add'),
    path('timetable/<int:pk>/edit/', views.timetable_edit, name='timetable_edit'),
    path('timetable/<int:pk>/delete/', views.timetable_delete, name='timetable_delete'),
    path('timetable/<int:pk>/move/', views.timetable_move, name='timetable_move'),

    path('free-time/', views.free_time_view, name='free_time'),
    path('ai-assistant/', views.ai_assistant_view, name='ai_assistant'),

    path('assignments/', views.assignment_list, name='assignment_list'),
    path('assignments/<int:pk>/toggle/', views.assignment_toggle, name='assignment_toggle'),
    path('assignments/<int:pk>/delete/', views.assignment_delete, name='assignment_delete'),

    path('exams/', views.exam_list, name='exam_list'),
    path('exams/<int:pk>/delete/', views.exam_delete, name='exam_delete'),

    path('goals/', views.goal_list, name='goal_list'),
    path('goals/<int:pk>/delete/', views.goal_delete, name='goal_delete'),

    path('reminders/', views.reminder_list, name='reminder_list'),
    path('reminders/<int:pk>/toggle/', views.reminder_toggle, name='reminder_toggle'),
    path('reminders/<int:pk>/delete/', views.reminder_delete, name='reminder_delete'),

    path('sessions/', views.session_list, name='session_list'),
    path('sessions/<int:pk>/delete/', views.session_delete, name='session_delete'),

    path('progress/', views.progress_view, name='progress'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('theme/toggle/', views.toggle_theme, name='toggle_theme'),
]
