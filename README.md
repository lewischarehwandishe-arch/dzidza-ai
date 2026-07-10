# DzidzaAI 

A Django web app for students to manage their timetable, discover free time
automatically, get AI-style study recommendations, track reminders, and
monitor study progress — all scoped to each logged-in student.

## Features

- **Timetable management** — add/edit/delete weekly class blocks (subject,
  teacher, day, time, location, study type). Drag-and-drop between days on
  the Timetable page.
- **Automatic free time detection** — gaps between classes (within a
  06:00–23:00 study window) are calculated on the fly and shown with
  duration, start/end time, and suggested activities.
- **Smart study recommendations** — a rule-based "AI assistant"
  (`planner/engine.py`) ranks subjects by exam urgency, performance score,
  pending assignments, and active goals, then splits free time into study +
  break blocks.
- **Wellness reminders** — burnout-prevention nudges appear on the dashboard
  once continuous study time crosses 45/90 minutes.
- **Reminders** — homework, assignments, revision, exams, projects, with
  push / email / in-app notification flags (in-app is fully wired; push and
  email are modeled and ready to connect to a real sender, e.g. via Celery +
  `django.core.mail`).
- **AI Study Assistant page** — daily timeline plan, weekly plan grid,
  priority subjects, and countdown revision schedules before exams.
- **Dashboard** — today's/upcoming classes, current free time + live
  recommendation, reminders, pending assignments, weekly/total study hours,
  break stats, upcoming exams.
- **Progress tracking** — hours per subject, weekly and 6-month trends
  (Chart.js), assignment completion rate, and a simple productivity score.
- **Modern UI** — light/dark mode (persisted client-side), responsive
  sidebar/mobile nav, color-coded subjects, custom design system (no
  generic Bootstrap look).

## Requirements

- Python 3.10+
- pip

## Setup

```bash
cd smartstudy
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser # optional, for /admin/
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`, register a student account, then:

1. Go to **Subjects** and add a few subjects (set a performance score).
2. Go to **Timetable** and add your weekly classes.
3. Visit **Free Time** and **AI Assistant** to see auto-detected gaps and
   recommendations.
4. Add **Assignments**, **Exams**, **Goals**, and **Reminders** to sharpen
   the recommendations.
5. Log **Study Sessions** to populate the **Progress** charts and trigger
   wellness reminders.

## Project layout

```
smartstudy/
  smartstudy/          project settings, urls
  planner/
    models.py          Subject, TimetableEntry, Assignment, ExamSchedule,
                        StudyGoal, Reminder, StudySession, Notification
    engine.py           free-time detection + recommendation/wellness engine
    forms.py, views.py, urls.py, admin.py
    templatetags/       small template helpers
    static/planner/     CSS design system + JS (theme, drag & drop)
  templates/            base layout, auth pages, all planner pages
```

## Notes on scaling & production

- Data is scoped per-user via `request.user` everywhere (students only ever
  see their own rows) and every query is filtered by `student=request.user`.
- For thousands of students, swap SQLite for PostgreSQL (`DATABASES` in
  `settings.py`), add DB indexes on `(student, day_of_week)` /
  `(student, remind_at)` if needed, and put `manage.py runserver` behind a
  real WSGI/ASGI server (gunicorn/uvicorn) with a task queue (Celery + Redis)
  to actually dispatch push/email notifications for `Reminder` objects.
- `DEBUG = True` and `SECRET_KEY` in `settings.py` are dev defaults — set
  real environment-based values before deploying.
