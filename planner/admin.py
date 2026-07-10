from django.contrib import admin
from .models import (
    Subject, TimetableEntry, Assignment, ExamSchedule,
    StudyGoal, Reminder, StudySession, Notification
)

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'student', 'performance_score', 'color')
    list_filter = ('student',)
    search_fields = ('name',)

@admin.register(TimetableEntry)
class TimetableEntryAdmin(admin.ModelAdmin):
    list_display = ('subject', 'student', 'day_of_week', 'start_time', 'end_time', 'study_type')
    list_filter = ('day_of_week', 'study_type')

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'student', 'due_date', 'priority', 'completed')
    list_filter = ('priority', 'completed')

@admin.register(ExamSchedule)
class ExamScheduleAdmin(admin.ModelAdmin):
    list_display = ('subject', 'student', 'exam_date')

@admin.register(StudyGoal)
class StudyGoalAdmin(admin.ModelAdmin):
    list_display = ('goal_text', 'student', 'subject', 'target_hours_per_week', 'is_active')

@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'category', 'remind_at', 'is_done')
    list_filter = ('category', 'is_done')

@admin.register(StudySession)
class StudySessionAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'session_type', 'start_time', 'end_time', 'status')
    list_filter = ('session_type', 'status')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('student', 'message', 'is_read', 'created_at')
