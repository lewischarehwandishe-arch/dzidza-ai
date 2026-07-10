// ---- Theme (light/dark) ----
(function () {
  const stored = localStorage.getItem('ssp-theme');
  const theme = stored || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', theme);
})();

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('ssp-theme', next);
  const icon = document.getElementById('theme-icon');
  if (icon) icon.textContent = next === 'dark' ? '☀️' : '🌙';
}

document.addEventListener('DOMContentLoaded', () => {
  const icon = document.getElementById('theme-icon');
  if (icon) icon.textContent = document.documentElement.getAttribute('data-theme') === 'dark' ? '☀️' : '🌙';

  // Mobile sidebar
  const menuBtn = document.getElementById('menu-btn');
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebar-backdrop');
  if (menuBtn && sidebar && backdrop) {
    menuBtn.addEventListener('click', () => {
      sidebar.classList.add('open');
      backdrop.classList.add('open');
    });
    backdrop.addEventListener('click', () => {
      sidebar.classList.remove('open');
      backdrop.classList.remove('open');
    });
  }

  initTimetableDragDrop();
});

// ---- Timetable drag & drop ----
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return '';
}

function initTimetableDragDrop() {
  const entries = document.querySelectorAll('.tt-entry[draggable="true"]');
  const days = document.querySelectorAll('.tt-day');
  if (!entries.length || !days.length) return;

  entries.forEach(el => {
    el.addEventListener('dragstart', (e) => {
      e.dataTransfer.setData('text/plain', el.dataset.id);
      el.classList.add('dragging');
    });
    el.addEventListener('dragend', () => el.classList.remove('dragging'));
  });

  days.forEach(day => {
    day.addEventListener('dragover', (e) => { e.preventDefault(); day.classList.add('drag-over'); });
    day.addEventListener('dragleave', () => day.classList.remove('drag-over'));
    day.addEventListener('drop', async (e) => {
      e.preventDefault();
      day.classList.remove('drag-over');
      const id = e.dataTransfer.getData('text/plain');
      const newDay = day.dataset.day;
      try {
        const res = await fetch(`/timetable/${id}/move/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
          body: JSON.stringify({ day_of_week: newDay }),
        });
        const data = await res.json();
        if (data.ok) {
          location.reload();
        } else {
          alert(data.error || 'Could not move this entry — it may overlap another class.');
        }
      } catch (err) {
        alert('Network error while moving entry.');
      }
    });
  });
}
