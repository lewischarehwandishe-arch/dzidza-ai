"""
The 'AI Study Assistant' engine.

This is deliberately implemented as transparent, explainable rule-based logic
(no external AI API required) so the whole app runs standalone. It covers:

  - Free time detection between timetable entries
  - Smart study recommendations (exam urgency, low performance, pending
    assignments, active goals)
  - Wellness / break reminders (Pomodoro-style burnout prevention)
  - Daily & weekly plan generation
"""
import datetime
from django.utils import timezone

from .models import DAY_START, DAY_END, TimetableEntry, Assignment, ExamSchedule, StudyGoal, StudySession

ACTIVITY_LIBRARY = [
    "Review previous lessons",
    "Complete pending assignments",
    "Practice quizzes",
    "Read study notes",
    "Watch educational videos",
    "Work on projects",
]

BREAK_TIPS = [
    "Drink some water and stretch.",
    "Take a short walk before your next study session.",
    "Rest your eyes — look at something 20 feet away for 20 seconds.",
    "Do a quick breathing exercise to reset focus.",
    "Tidy your desk before the next session.",
]


def _combine(day, t):
    return datetime.datetime.combine(day, t)


def get_free_slots_for_day(student, day_date):
    """Return list of dicts: {start, end, duration_minutes} of free gaps on a given date."""
    weekday = day_date.weekday()
    entries = list(
        TimetableEntry.objects.filter(student=student, day_of_week=weekday).order_by('start_time')
    )

    slots = []
    cursor = DAY_START
    for entry in entries:
        if entry.start_time > cursor:
            slots.append((cursor, entry.start_time))
        if entry.end_time > cursor:
            cursor = entry.end_time
    if cursor < DAY_END:
        slots.append((cursor, DAY_END))

    free_slots = []
    for start, end in slots:
        duration = int((_combine(day_date, end) - _combine(day_date, start)).total_seconds() // 60)
        if duration >= 15:  # ignore tiny unusable gaps
            free_slots.append({
                'start': start,
                'end': end,
                'duration_minutes': duration,
            })
    return free_slots


def get_current_free_slot(student, now=None):
    """If the student is free right now (within study hours), return that slot, else None."""
    now = now or timezone.localtime()
    today_slots = get_free_slots_for_day(student, now.date())
    for slot in today_slots:
        if slot['start'] <= now.time() <= slot['end']:
            return slot
    return None


def get_priority_subjects(student, limit=5):
    """
    Rank subjects by urgency using:
      - days until next exam (sooner = higher priority)
      - performance score (lower = higher priority)
      - pending assignment due dates (sooner = higher priority)
      - active study goals
    Returns a list of dicts sorted by descending priority score.
    """
    subjects = student.subjects.all()
    today = timezone.localdate()
    ranked = []

    for subject in subjects:
        score = 0.0
        reasons = []

        next_exam = subject.exams.filter(exam_date__date__gte=today).order_by('exam_date').first()
        if next_exam:
            days_left = max(next_exam.days_remaining, 0)
            exam_weight = max(0, 30 - days_left) * 3
            score += exam_weight
            if days_left <= 7:
                reasons.append(f"exam in {days_left} day(s)")

        if subject.performance_score < 75:
            perf_weight = (75 - subject.performance_score) * 1.5
            score += perf_weight
            reasons.append(f"performance at {subject.performance_score}%")

        pending = subject.assignments.filter(completed=False).order_by('due_date')
        if pending.exists():
            nearest = pending.first()
            days_left = (nearest.due_date.date() - today).days
            urgency = max(0, 14 - days_left) * 2
            score += urgency
            reasons.append(f"{pending.count()} pending assignment(s)")

        if subject.goals.filter(is_active=True).exists():
            score += 5
            reasons.append("active study goal")

        if score > 0 or reasons:
            ranked.append({'subject': subject, 'score': round(score, 1), 'reasons': reasons})

    ranked.sort(key=lambda r: r['score'], reverse=True)
    return ranked[:limit] if limit else ranked


def build_activity_for_subject(subject, index=0):
    """Pick a recommended activity phrase, biased by upcoming context."""
    today = timezone.localdate()
    if subject.exams.filter(exam_date__date__gte=today).exists():
        return "Practice quizzes"
    if subject.assignments.filter(completed=False).exists():
        return "Complete pending assignments"
    if subject.performance_score < 75:
        return "Review previous lessons"
    return ACTIVITY_LIBRARY[index % len(ACTIVITY_LIBRARY)]


def recommend_for_slot(student, slot_duration_minutes):
    """
    Given a free slot's duration, split it across the highest-priority
    subjects, inserting short breaks, mimicking:
    'You have a 2-hour free period. Study Maths 1h, Physics 45m, break 15m.'
    """
    priorities = get_priority_subjects(student, limit=3)
    if not priorities:
        return {
            'blocks': [],
            'summary': "No subjects set up yet — add subjects and a timetable to unlock personalised recommendations.",
        }

    remaining = slot_duration_minutes
    blocks = []
    for i, item in enumerate(priorities):
        if remaining < 15:
            break
        # allocate roughly proportional chunks, capped at 60 min per subject before a break
        chunk = min(60, remaining - 15 if len(priorities) > i + 1 else remaining)
        chunk = max(chunk, 15)
        activity = build_activity_for_subject(item['subject'], i)
        blocks.append({
            'subject': item['subject'],
            'minutes': chunk,
            'activity': activity,
            'reasons': item['reasons'],
        })
        remaining -= chunk
        if remaining >= 15 and i < len(priorities) - 1:
            blocks.append({'subject': None, 'minutes': 15, 'activity': 'Short break', 'reasons': []})
            remaining -= 15

    if remaining >= 15:
        blocks.append({'subject': None, 'minutes': remaining, 'activity': 'Free / rest time', 'reasons': []})

    summary_parts = [f"{b['minutes']}m {b['subject'].name}" for b in blocks if b['subject']]
    if summary_parts:
        summary = f"You have {slot_duration_minutes} minutes free. Suggested: " + ", ".join(summary_parts) + "."
    else:
        summary = "Enjoy your free time — no urgent study items right now."
    return {'blocks': blocks, 'summary': summary}


def wellness_check(student, now=None):
    """
    Look at today's completed/ongoing study sessions and return a wellness
    message if the student has been grinding without a break.
    """
    now = now or timezone.localtime()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    sessions = StudySession.objects.filter(
        student=student, session_type='study', start_time__gte=today_start, start_time__lte=now
    ).order_by('start_time')

    if not sessions:
        return None

    # sum continuous study minutes since the last break
    continuous_minutes = 0
    last_end = None
    for s in sessions:
        if last_end and (s.start_time - last_end) > datetime.timedelta(minutes=10):
            continuous_minutes = 0  # a break happened
        continuous_minutes += s.duration_minutes
        last_end = s.end_time

    import random
    if continuous_minutes >= 90:
        return {
            'level': 'warning',
            'message': f"You've studied for {continuous_minutes} minutes straight. Take a 15-minute break — {random.choice(BREAK_TIPS)}",
        }
    elif continuous_minutes >= 45:
        return {
            'level': 'info',
            'message': f"You've studied for {continuous_minutes} minutes. {random.choice(BREAK_TIPS)}",
        }
    return None


def generate_daily_plan(student, day_date=None):
    """Generate a full-day plan: classes + recommended study blocks for each free slot."""
    day_date = day_date or timezone.localdate()
    classes = TimetableEntry.objects.filter(student=student, day_of_week=day_date.weekday()).order_by('start_time')
    free_slots = get_free_slots_for_day(student, day_date)

    plan = []
    for entry in classes:
        plan.append({'type': 'class', 'start': entry.start_time, 'end': entry.end_time, 'entry': entry})
    for slot in free_slots:
        rec = recommend_for_slot(student, slot['duration_minutes'])
        plan.append({'type': 'free', 'start': slot['start'], 'end': slot['end'],
                      'duration_minutes': slot['duration_minutes'], 'recommendation': rec})
    plan.sort(key=lambda x: x['start'])
    return plan


def generate_weekly_plan(student, week_start=None):
    """Generate a 7-day plan starting from week_start (defaults to this week's Monday)."""
    today = timezone.localdate()
    week_start = week_start or (today - datetime.timedelta(days=today.weekday()))
    week = []
    for i in range(7):
        day = week_start + datetime.timedelta(days=i)
        week.append({'date': day, 'plan': generate_daily_plan(student, day)})
    return week


def revision_schedule(student, exam):
    """Suggest a countdown revision schedule leading up to an exam."""
    days_left = max(exam.days_remaining, 0)
    schedule = []
    if days_left <= 0:
        return schedule
    focus_days = min(days_left, 7)
    for i in range(focus_days):
        day_offset = days_left - i
        if day_offset <= 1:
            activity = "Final review + practice past papers"
        elif day_offset <= 3:
            activity = "Practice quizzes & timed exercises"
        else:
            activity = "Review notes & summarise key topics"
        schedule.append({'days_before_exam': day_offset, 'activity': activity})
    return schedule
