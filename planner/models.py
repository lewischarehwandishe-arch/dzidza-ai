import datetime
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


DAYS_OF_WEEK = [
    (0, 'Monday'),
    (1, 'Tuesday'),
    (2, 'Wednesday'),
    (3, 'Thursday'),
    (4, 'Friday'),
    (5, 'Saturday'),
    (6, 'Sunday'),
]

STUDY_TYPES = [
    ('class', 'Class'),
    ('self_study', 'Self-Study'),
    ('assignment', 'Assignment'),
    ('revision', 'Revision'),
]

PRIORITY_LEVELS = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
]

REMINDER_CATEGORIES = [
    ('homework', 'Homework'),
    ('assignment', 'Assignment'),
    ('revision', 'Revision Session'),
    ('exam', 'Exam Preparation'),
    ('project', 'Project Deadline'),
]

SUBJECT_COLORS = [
    '#4F46E5', '#059669', '#DC2626', '#D97706', '#7C3AED',
    '#DB2777', '#0891B2', '#65A30D', '#EA580C', '#4338CA',
]

# Study-hours window used for free-time detection (24h clock)
DAY_START = datetime.time(6, 0)
DAY_END = datetime.time(23, 0)


class Subject(models.Model):
    """A subject/course belonging to a student. Color-coded across the UI."""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default='#4F46E5')
    performance_score = models.PositiveSmallIntegerField(
        default=70, help_text='Latest performance score (0-100) used for study prioritisation.'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ('student', 'name')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.color:
            count = Subject.objects.filter(student=self.student).count()
            self.color = SUBJECT_COLORS[count % len(SUBJECT_COLORS)]
        super().save(*args, **kwargs)


class TimetableEntry(models.Model):
    """A single recurring weekly timetable block for a student."""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='timetable_entries')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='timetable_entries')
    teacher = models.CharField(max_length=100, blank=True)
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=100, blank=True)
    study_type = models.CharField(max_length=20, choices=STUDY_TYPES, default='class')

    class Meta:
        ordering = ['day_of_week', 'start_time']
        verbose_name_plural = 'Timetable entries'

    def __str__(self):
        return f"{self.subject.name} ({self.get_day_of_week_display()} {self.start_time}-{self.end_time})"

    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError('End time must be after start time.')
        if self.student_id and self.day_of_week is not None and self.start_time and self.end_time:
            overlapping = TimetableEntry.objects.filter(
                student=self.student, day_of_week=self.day_of_week
            ).exclude(pk=self.pk)
            for entry in overlapping:
                if self.start_time < entry.end_time and self.end_time > entry.start_time:
                    raise ValidationError(
                        f'This overlaps with "{entry.subject.name}" '
                        f'({entry.start_time.strftime("%H:%M")}-{entry.end_time.strftime("%H:%M")}) on '
                        f'{self.get_day_of_week_display()}.'
                    )

    @property
    def duration_minutes(self):
        dummy = datetime.date(2000, 1, 1)
        return int((datetime.datetime.combine(dummy, self.end_time) -
                     datetime.datetime.combine(dummy, self.start_time)).total_seconds() // 60)


class Assignment(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assignments')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    due_date = models.DateTimeField()
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['completed', 'due_date']

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        return not self.completed and self.due_date < timezone.now()


class ExamSchedule(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exams')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exams')
    title = models.CharField(max_length=150, default='Exam')
    exam_date = models.DateTimeField()
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['exam_date']

    def __str__(self):
        return f"{self.subject.name} exam on {self.exam_date:%Y-%m-%d}"

    @property
    def days_remaining(self):
        delta = self.exam_date.date() - timezone.localdate()
        return delta.days


class StudyGoal(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='goals')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='goals', null=True, blank=True)
    goal_text = models.CharField(max_length=200)
    target_hours_per_week = models.DecimalField(max_digits=4, decimal_places=1, default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.goal_text


class Reminder(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reminders')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, related_name='reminders', null=True, blank=True)
    title = models.CharField(max_length=150)
    message = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=REMINDER_CATEGORIES, default='homework')
    remind_at = models.DateTimeField()
    notify_push = models.BooleanField(default=True)
    notify_email = models.BooleanField(default=False)
    notify_inapp = models.BooleanField(default=True)
    is_done = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['remind_at']

    def __str__(self):
        return self.title

    @property
    def is_due_soon(self):
        return not self.is_done and self.remind_at <= timezone.now() + datetime.timedelta(hours=24)


class StudySession(models.Model):
    SESSION_TYPES = [('study', 'Study'), ('break', 'Break')]
    STATUS_CHOICES = [('planned', 'Planned'), ('completed', 'Completed'), ('missed', 'Missed')]

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='study_sessions')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='study_sessions', null=True, blank=True)
    session_type = models.CharField(max_length=10, choices=SESSION_TYPES, default='study')
    activity = models.CharField(max_length=150, blank=True, help_text='e.g. Review notes, Practice quiz')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='planned')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.get_session_type_display()} - {self.subject or 'General'} ({self.start_time:%Y-%m-%d %H:%M})"

    @property
    def duration_minutes(self):
        return int((self.end_time - self.start_time).total_seconds() // 60)


class Notification(models.Model):
    """In-app notification feed (also used as the delivery record for push/email)."""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.message
