import datetime
import json
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    RegisterForm, SubjectForm, TimetableEntryForm, AssignmentForm,
    ExamForm, StudyGoalForm, ReminderForm, StudySessionForm
)
from .models import (
    Subject, TimetableEntry, Assignment, ExamSchedule, StudyGoal,
    Reminder, StudySession, Notification, DAYS_OF_WEEK
)
from . import engine


# ---------------------------------------------------------------- auth ----

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            Notification.objects.create(student=user, message="Welcome to DzidzaAI! Add your subjects and timetable to get started.")
            messages.success(request, "Account created — welcome!")
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


# ----------------------------------------------------------- dashboard ----

@login_required
def dashboard(request):
    student = request.user
    now = timezone.localtime()
    today = now.date()
    weekday = today.weekday()

    todays_classes = TimetableEntry.objects.filter(student=student, day_of_week=weekday).order_by('start_time')
    upcoming_classes = TimetableEntry.objects.filter(student=student, day_of_week__gt=weekday).order_by('day_of_week', 'start_time')[:5]
    if not upcoming_classes:
        upcoming_classes = TimetableEntry.objects.filter(student=student).order_by('day_of_week', 'start_time')[:5]

    current_free_slot = engine.get_current_free_slot(student, now)
    current_recommendation = None
    if current_free_slot:
        current_recommendation = engine.recommend_for_slot(student, current_free_slot['duration_minutes'])

    upcoming_reminders = Reminder.objects.filter(student=student, is_done=False, remind_at__gte=now).order_by('remind_at')[:5]
    pending_assignments = Assignment.objects.filter(student=student, completed=False).order_by('due_date')[:6]
    upcoming_exams = ExamSchedule.objects.filter(student=student, exam_date__gte=now).order_by('exam_date')[:4]

    week_start = today - datetime.timedelta(days=weekday)
    week_sessions = StudySession.objects.filter(
        student=student, session_type='study', status='completed',
        start_time__date__gte=week_start
    )
    weekly_minutes = sum(s.duration_minutes for s in week_sessions)
    total_minutes = sum(
        s.duration_minutes for s in StudySession.objects.filter(student=student, session_type='study', status='completed')
    )
    break_minutes = sum(
        s.duration_minutes for s in StudySession.objects.filter(student=student, session_type='break', status='completed')
    )
    missed_sessions = StudySession.objects.filter(student=student, status='missed').count()

    wellness = engine.wellness_check(student, now)
    priority_subjects = engine.get_priority_subjects(student, limit=4)

    context = {
        'todays_classes': todays_classes,
        'upcoming_classes': upcoming_classes,
        'current_free_slot': current_free_slot,
        'current_recommendation': current_recommendation,
        'upcoming_reminders': upcoming_reminders,
        'pending_assignments': pending_assignments,
        'upcoming_exams': upcoming_exams,
        'weekly_hours': round(weekly_minutes / 60, 1),
        'total_hours': round(total_minutes / 60, 1),
        'break_minutes': break_minutes,
        'missed_sessions': missed_sessions,
        'wellness': wellness,
        'priority_subjects': priority_subjects,
        'today': today,
        'subjects_count': Subject.objects.filter(student=student).count(),
    }
    return render(request, 'planner/dashboard.html', context)


# ---------------------------------------------------------- subjects ------

@login_required
def subject_list(request):
    subjects = Subject.objects.filter(student=request.user)
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.student = request.user
            subject.save()
            messages.success(request, f'Subject "{subject.name}" added.')
            return redirect('subject_list')
    else:
        form = SubjectForm()
    return render(request, 'planner/subject_list.html', {'subjects': subjects, 'form': form})


@login_required
def subject_delete(request, pk):
    subject = get_object_or_404(Subject, pk=pk, student=request.user)
    if request.method == 'POST':
        subject.delete()
        messages.success(request, 'Subject deleted.')
    return redirect('subject_list')


# --------------------------------------------------------- timetable ------

@login_required
def timetable_view(request):
    entries = TimetableEntry.objects.filter(student=request.user).select_related('subject')
    grouped = defaultdict(list)
    for e in entries:
        grouped[e.day_of_week].append(e)
    days = [(num, label, grouped.get(num, [])) for num, label in DAYS_OF_WEEK]
    free_by_day = {num: engine.get_free_slots_for_day(request.user, _next_date_for_weekday(num)) for num, _ in DAYS_OF_WEEK}
    return render(request, 'planner/timetable.html', {
        'days': days, 'free_by_day': free_by_day,
        'has_subjects': Subject.objects.filter(student=request.user).exists(),
    })


def _next_date_for_weekday(weekday):
    today = timezone.localdate()
    delta = (weekday - today.weekday()) % 7
    return today + datetime.timedelta(days=delta)


@login_required
def timetable_add(request):
    if request.method == 'POST':
        form = TimetableEntryForm(request.POST, student=request.user)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.student = request.user
            try:
                entry.full_clean()
                entry.save()
                messages.success(request, 'Timetable entry added.')
                return redirect('timetable')
            except ValidationError as e:
                for err in e.messages:
                    form.add_error(None, err)
    else:
        form = TimetableEntryForm(student=request.user)
    return render(request, 'planner/timetable_form.html', {'form': form, 'title': 'Add Timetable Entry'})


@login_required
def timetable_edit(request, pk):
    entry = get_object_or_404(TimetableEntry, pk=pk, student=request.user)
    if request.method == 'POST':
        form = TimetableEntryForm(request.POST, instance=entry, student=request.user)
        if form.is_valid():
            updated = form.save(commit=False)
            try:
                updated.full_clean()
                updated.save()
                messages.success(request, 'Timetable entry updated.')
                return redirect('timetable')
            except ValidationError as e:
                for err in e.messages:
                    form.add_error(None, err)
    else:
        form = TimetableEntryForm(instance=entry, student=request.user)
    return render(request, 'planner/timetable_form.html', {'form': form, 'title': 'Edit Timetable Entry'})


@login_required
def timetable_delete(request, pk):
    entry = get_object_or_404(TimetableEntry, pk=pk, student=request.user)
    if request.method == 'POST':
        entry.delete()
        messages.success(request, 'Timetable entry deleted.')
    return redirect('timetable')


@login_required
@require_POST
def timetable_move(request, pk):
    """AJAX endpoint used by the drag-and-drop timetable grid."""
    entry = get_object_or_404(TimetableEntry, pk=pk, student=request.user)
    try:
        data = json.loads(request.body)
        new_day = int(data['day_of_week'])
    except (KeyError, ValueError, json.JSONDecodeError):
        return JsonResponse({'ok': False, 'error': 'Invalid payload'}, status=400)

    old_day = entry.day_of_week
    entry.day_of_week = new_day
    try:
        entry.full_clean()
        entry.save()
    except ValidationError as e:
        entry.day_of_week = old_day
        return JsonResponse({'ok': False, 'error': ' '.join(e.messages)}, status=400)
    return JsonResponse({'ok': True})


# -------------------------------------------------------- free time -------

@login_required
def free_time_view(request):
    today = timezone.localdate()
    days_data = []
    for i in range(7):
        day = today + datetime.timedelta(days=i)
        slots = engine.get_free_slots_for_day(request.user, day)
        for slot in slots:
            slot['recommendation'] = engine.recommend_for_slot(request.user, slot['duration_minutes'])
        days_data.append({'date': day, 'slots': slots})
    return render(request, 'planner/free_time.html', {'days_data': days_data})


# ------------------------------------------------------- AI assistant -----

@login_required
def ai_assistant_view(request):
    student = request.user
    daily_plan = engine.generate_daily_plan(student)
    weekly_plan = engine.generate_weekly_plan(student)
    upcoming_exams = ExamSchedule.objects.filter(student=student, exam_date__gte=timezone.now()).order_by('exam_date')[:3]
    revision_plans = [{'exam': e, 'schedule': engine.revision_schedule(student, e)} for e in upcoming_exams]
    priority_subjects = engine.get_priority_subjects(student, limit=6)
    return render(request, 'planner/ai_assistant.html', {
        'daily_plan': daily_plan,
        'weekly_plan': weekly_plan,
        'revision_plans': revision_plans,
        'priority_subjects': priority_subjects,
    })


# -------------------------------------------------------- assignments -----

@login_required
def assignment_list(request):
    assignments = Assignment.objects.filter(student=request.user).select_related('subject')
    if request.method == 'POST':
        form = AssignmentForm(request.POST, student=request.user)
        if form.is_valid():
            a = form.save(commit=False)
            a.student = request.user
            a.save()
            messages.success(request, 'Assignment added.')
            return redirect('assignment_list')
    else:
        form = AssignmentForm(student=request.user)
    return render(request, 'planner/assignment_list.html', {'assignments': assignments, 'form': form})


@login_required
def assignment_toggle(request, pk):
    a = get_object_or_404(Assignment, pk=pk, student=request.user)
    a.completed = not a.completed
    a.save()
    return redirect('assignment_list')


@login_required
def assignment_delete(request, pk):
    a = get_object_or_404(Assignment, pk=pk, student=request.user)
    if request.method == 'POST':
        a.delete()
        messages.success(request, 'Assignment deleted.')
    return redirect('assignment_list')


# --------------------------------------------------------------- exams ----

@login_required
def exam_list(request):
    exams = ExamSchedule.objects.filter(student=request.user).select_related('subject')
    if request.method == 'POST':
        form = ExamForm(request.POST, student=request.user)
        if form.is_valid():
            e = form.save(commit=False)
            e.student = request.user
            e.save()
            messages.success(request, 'Exam added.')
            return redirect('exam_list')
    else:
        form = ExamForm(student=request.user)
    return render(request, 'planner/exam_list.html', {'exams': exams, 'form': form})


@login_required
def exam_delete(request, pk):
    e = get_object_or_404(ExamSchedule, pk=pk, student=request.user)
    if request.method == 'POST':
        e.delete()
        messages.success(request, 'Exam removed.')
    return redirect('exam_list')


# --------------------------------------------------------------- goals ----

@login_required
def goal_list(request):
    goals = StudyGoal.objects.filter(student=request.user).select_related('subject')
    if request.method == 'POST':
        form = StudyGoalForm(request.POST, student=request.user)
        if form.is_valid():
            g = form.save(commit=False)
            g.student = request.user
            g.save()
            messages.success(request, 'Study goal added.')
            return redirect('goal_list')
    else:
        form = StudyGoalForm(student=request.user)
    return render(request, 'planner/goal_list.html', {'goals': goals, 'form': form})


@login_required
def goal_delete(request, pk):
    g = get_object_or_404(StudyGoal, pk=pk, student=request.user)
    if request.method == 'POST':
        g.delete()
        messages.success(request, 'Goal deleted.')
    return redirect('goal_list')


# ----------------------------------------------------------- reminders ----

@login_required
def reminder_list(request):
    reminders = Reminder.objects.filter(student=request.user).select_related('subject')
    if request.method == 'POST':
        form = ReminderForm(request.POST, student=request.user)
        if form.is_valid():
            r = form.save(commit=False)
            r.student = request.user
            r.save()
            Notification.objects.create(student=request.user, message=f'Reminder set: "{r.title}"')
            messages.success(request, 'Reminder created.')
            return redirect('reminder_list')
    else:
        form = ReminderForm(student=request.user)
    return render(request, 'planner/reminder_list.html', {'reminders': reminders, 'form': form})


@login_required
def reminder_toggle(request, pk):
    r = get_object_or_404(Reminder, pk=pk, student=request.user)
    r.is_done = not r.is_done
    r.save()
    return redirect('reminder_list')


@login_required
def reminder_delete(request, pk):
    r = get_object_or_404(Reminder, pk=pk, student=request.user)
    if request.method == 'POST':
        r.delete()
        messages.success(request, 'Reminder deleted.')
    return redirect('reminder_list')


# ------------------------------------------------------- study sessions ---

@login_required
def session_list(request):
    sessions = StudySession.objects.filter(student=request.user).select_related('subject')[:50]
    if request.method == 'POST':
        form = StudySessionForm(request.POST, student=request.user)
        if form.is_valid():
            s = form.save(commit=False)
            s.student = request.user
            s.save()
            messages.success(request, 'Study session logged.')
            return redirect('session_list')
    else:
        form = StudySessionForm(student=request.user, initial={
            'start_time': timezone.localtime().strftime('%Y-%m-%dT%H:%M'),
        })
    return render(request, 'planner/session_list.html', {'sessions': sessions, 'form': form})


@login_required
def session_delete(request, pk):
    s = get_object_or_404(StudySession, pk=pk, student=request.user)
    if request.method == 'POST':
        s.delete()
        messages.success(request, 'Session deleted.')
    return redirect('session_list')


# ------------------------------------------------------------- progress ---

@login_required
def progress_view(request):
    student = request.user
    today = timezone.localdate()
    week_start = today - datetime.timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    subjects = Subject.objects.filter(student=student)
    hours_per_subject = []
    for s in subjects:
        total_minutes = sum(
            sess.duration_minutes for sess in StudySession.objects.filter(
                student=student, subject=s, session_type='study', status='completed')
        )
        hours_per_subject.append({'subject': s.name, 'color': s.color, 'hours': round(total_minutes / 60, 2)})

    # weekly chart: minutes per weekday for the current week
    weekly_series = []
    for i in range(7):
        day = week_start + datetime.timedelta(days=i)
        minutes = sum(
            sess.duration_minutes for sess in StudySession.objects.filter(
                student=student, session_type='study', status='completed', start_time__date=day)
        )
        weekly_series.append({'day': day.strftime('%a'), 'minutes': minutes})

    # monthly totals (last 6 months)
    monthly_series = []
    cursor = month_start
    for i in range(5, -1, -1):
        year = cursor.year
        month = cursor.month - i
        while month <= 0:
            month += 12
            year -= 1
        minutes = sum(
            sess.duration_minutes for sess in StudySession.objects.filter(
                student=student, session_type='study', status='completed',
                start_time__year=year, start_time__month=month)
        )
        monthly_series.append({'label': f'{year}-{month:02d}', 'minutes': minutes})

    completed_sessions = StudySession.objects.filter(student=student, session_type='study', status='completed').count()
    missed_sessions = StudySession.objects.filter(student=student, session_type='study', status='missed').count()
    total_assignments = Assignment.objects.filter(student=student).count()
    completed_assignments = Assignment.objects.filter(student=student, completed=True).count()
    completion_rate = round((completed_assignments / total_assignments) * 100, 1) if total_assignments else 0

    # simple productivity score: weighted blend of session completion & assignment completion
    total_sessions = completed_sessions + missed_sessions
    session_rate = (completed_sessions / total_sessions * 100) if total_sessions else 0
    productivity_score = round((session_rate * 0.5) + (completion_rate * 0.5), 1)

    context = {
        'hours_per_subject': hours_per_subject,
        'weekly_series': weekly_series,
        'monthly_series': monthly_series,
        'completed_sessions': completed_sessions,
        'missed_sessions': missed_sessions,
        'completion_rate': completion_rate,
        'productivity_score': productivity_score,
        'hours_per_subject_json': json.dumps(hours_per_subject),
        'weekly_series_json': json.dumps(weekly_series),
        'monthly_series_json': json.dumps(monthly_series),
    }
    return render(request, 'planner/progress.html', context)


# --------------------------------------------------------- notifications --

@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(student=request.user)[:30]
    Notification.objects.filter(student=request.user, is_read=False).update(is_read=True)
    return render(request, 'planner/notifications.html', {'notifications': notifications})


@login_required
def toggle_theme(request):
    """No-op server route kept for progressive enhancement; theme is stored client-side."""
    return JsonResponse({'ok': True})
