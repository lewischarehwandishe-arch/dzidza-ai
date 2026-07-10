from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import (
    Subject, TimetableEntry, Assignment, ExamSchedule, StudyGoal, Reminder, StudySession
)


class StyledFormMixin:
    """Adds Bootstrap classes to every field automatically."""
    def _style(self):
        for name, field in self.fields.items():
            css = 'form-select' if isinstance(field.widget, (forms.Select, forms.SelectMultiple)) else 'form-control'
            if isinstance(field.widget, forms.CheckboxInput):
                css = 'form-check-input'
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (existing + ' ' + css).strip()


class RegisterForm(StyledFormMixin, UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class SubjectForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'color', 'performance_score']
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color'}),
            'performance_score': forms.NumberInput(attrs={'min': 0, 'max': 100}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()


class TimetableEntryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = TimetableEntry
        fields = ['subject', 'teacher', 'day_of_week', 'start_time', 'end_time', 'location', 'study_type']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        if student is not None:
            self.fields['subject'].queryset = Subject.objects.filter(student=student)
        self._style()

    def clean(self):
        cleaned = super().clean()
        return cleaned


class AssignmentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['subject', 'title', 'description', 'due_date', 'priority', 'completed']
        widgets = {'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'})}

    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        if student is not None:
            self.fields['subject'].queryset = Subject.objects.filter(student=student)
        self._style()


class ExamForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ExamSchedule
        fields = ['subject', 'title', 'exam_date', 'notes']
        widgets = {'exam_date': forms.DateTimeInput(attrs={'type': 'datetime-local'})}

    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        if student is not None:
            self.fields['subject'].queryset = Subject.objects.filter(student=student)
        self._style()


class StudyGoalForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = StudyGoal
        fields = ['subject', 'goal_text', 'target_hours_per_week', 'is_active']

    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        if student is not None:
            self.fields['subject'].queryset = Subject.objects.filter(student=student)
            self.fields['subject'].required = False
        self._style()


class ReminderForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Reminder
        fields = ['title', 'subject', 'category', 'message', 'remind_at',
                  'notify_push', 'notify_email', 'notify_inapp']
        widgets = {'remind_at': forms.DateTimeInput(attrs={'type': 'datetime-local'})}

    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        if student is not None:
            self.fields['subject'].queryset = Subject.objects.filter(student=student)
            self.fields['subject'].required = False
        self._style()


class StudySessionForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = StudySession
        fields = ['subject', 'session_type', 'activity', 'start_time', 'end_time', 'status']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, student=None, **kwargs):
        super().__init__(*args, **kwargs)
        if student is not None:
            self.fields['subject'].queryset = Subject.objects.filter(student=student)
            self.fields['subject'].required = False
        self._style()
