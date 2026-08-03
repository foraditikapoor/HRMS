// timezone cache refresh
(() => {
  const sidebar = document.getElementById('appSidebar');
  const toggle = document.querySelector('.sidebar-toggle');
  if (sidebar && toggle) {
    toggle.addEventListener('click', () => {
      const open = sidebar.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', String(open));
    });
    document.addEventListener('click', (event) => {
      if (window.innerWidth <= 900 && sidebar.classList.contains('is-open') && !sidebar.contains(event.target) && !toggle.contains(event.target)) {
        sidebar.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // Theme Manager
  function applyTheme(themePref) {
    let effective = themePref;
    if (!effective || effective === 'system') {
      effective = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    document.documentElement.setAttribute('data-bs-theme', effective);
    document.documentElement.setAttribute('data-theme', effective);
    if (document.body) {
      document.body.setAttribute('data-bs-theme', effective);
    }
    localStorage.setItem('hrms-theme-preference', themePref);
    localStorage.setItem('hrms-effective-theme', effective);
  }

  // Initial theme resolution
  const docPref = document.documentElement.getAttribute('data-theme-preference');
  const storedPref = localStorage.getItem('hrms-theme-preference');
  const initialPref = docPref || storedPref || 'light';
  applyTheme(initialPref);

  // Listen for OS system theme changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    const currentPref = localStorage.getItem('hrms-theme-preference') || 'system';
    if (currentPref === 'system') {
      applyTheme('system');
    }
  });

  window.setHrmsTheme = function(themePref) {
    applyTheme(themePref);
    fetch('/api/user-preferences/theme', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ theme: themePref })
    }).catch(err => console.error('Failed to sync theme:', err));
  };

  // Fallback and instant toggle handling for collapse dropdowns
  document.addEventListener('DOMContentLoaded', () => {
    // Attach live change listeners for theme radio buttons on Appearance Settings page
    ['themeLight', 'themeDark', 'themeSystem'].forEach(id => {
      const radio = document.getElementById(id);
      if (radio) {
        radio.addEventListener('change', (e) => {
          if (e.target.checked) {
            window.setHrmsTheme(e.target.value);
          }
        });
      }
    });

    // Auto-fill Start Date and End Date when date preset option changes
    function setupDateFilterSync(selectId, startId, endId) {
      const selectEl = document.getElementById(selectId);
      const startEl = document.getElementById(startId);
      const endEl = document.getElementById(endId);
      if (!selectEl || !startEl || !endEl) return;

      selectEl.addEventListener('change', () => {
        const val = selectEl.value;
        const today = new Date();
        const formatDate = (d) => {
          const year = d.getFullYear();
          const month = String(d.getMonth() + 1).padStart(2, '0');
          const day = String(d.getDate()).padStart(2, '0');
          return `${year}-${month}-${day}`;
        };

        if (val === 'today') {
          startEl.value = formatDate(today);
          endEl.value = formatDate(today);
        } else if (val === 'last_7') {
          const d = new Date(today);
          d.setDate(d.getDate() - 6);
          startEl.value = formatDate(d);
          endEl.value = formatDate(today);
        } else if (val === 'last_30') {
          const d = new Date(today);
          d.setDate(d.getDate() - 29);
          startEl.value = formatDate(d);
          endEl.value = formatDate(today);
        } else if (val === 'this_month') {
          const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
          startEl.value = formatDate(firstDay);
          endEl.value = formatDate(today);
        } else if (val === 'all') {
          startEl.value = '';
          endEl.value = '';
        }
      });
    }

    setupDateFilterSync('employeeDateFilterSelect', 'employeeStartDateInput', 'employeeEndDateInput');
    setupDateFilterSync('adminDateFilterSelect', 'adminStartDateInput', 'adminEndDateInput');

    document.querySelectorAll('[data-bs-toggle="collapse"]').forEach((toggleBtn) => {
      toggleBtn.addEventListener('click', (e) => {
        const targetSelector = toggleBtn.getAttribute('href') || toggleBtn.getAttribute('data-bs-target');
        if (targetSelector && targetSelector.startsWith('#')) {
          const targetEl = document.querySelector(targetSelector);
          if (targetEl && typeof bootstrap === 'undefined') {
            e.preventDefault();
            const isOpen = targetEl.classList.toggle('show');
            toggleBtn.setAttribute('aria-expanded', String(isOpen));
          }
        }
      });
    });

    if (document.getElementById('notifDropdownToggle')) {
      fetchNotifications();
      setInterval(fetchNotifications, 30000);
    }
  });

  function fetchNotifications() {
    fetch('/api/notifications?unread_only=1')
      .then(res => res.json())
      .then(data => {
        const notifBadge = document.getElementById('notifBadge');
        const notifDot = document.getElementById('notifDot');
        const notifList = document.getElementById('notifDropdownList');
        if (!notifList) return;

        if (data.unread_count > 0) {
          if (notifBadge) {
            notifBadge.textContent = data.unread_count > 99 ? '99+' : data.unread_count;
            notifBadge.classList.remove('d-none');
          }
          if (notifDot) notifDot.classList.remove('d-none');
        } else {
          if (notifBadge) notifBadge.classList.add('d-none');
          if (notifDot) notifDot.classList.add('d-none');
        }

        if (data.notifications && data.notifications.length > 0) {
          notifList.innerHTML = data.notifications.map(n => `
            <a href="${n.link || '/notifications'}" onclick="markNotificationRead(event, ${n.id}, '${n.link || ''}')" class="list-group-item list-group-item-action p-3 border-bottom bg-light">
              <div class="d-flex w-100 justify-content-between align-items-center mb-1">
                <strong class="mb-0 small text-dark fw-bold text-primary">${escapeHtml(n.title)}</strong>
                <small class="text-muted" style="font-size: 11px;">${escapeHtml(n.created_at)}</small>
              </div>
              <p class="mb-0 text-secondary" style="font-size: 12px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${escapeHtml(n.message)}</p>
            </a>
          `).join('');
        } else {
          notifList.innerHTML = '<div class="text-center py-4 text-muted small"><i class="bi bi-bell-slash d-block mb-1 fs-5"></i>No unread notifications</div>';
        }
      })
      .catch(err => console.error('Failed to fetch notifications:', err));
  }

  function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  window.markNotificationRead = function(event, notifId, targetUrl) {
    // Immediate optimistic removal from active dropdown
    const itemEl = event.currentTarget;
    if (itemEl && itemEl.parentNode) {
      itemEl.remove();
    }
    const notifBadge = document.getElementById('notifBadge');
    const notifDot = document.getElementById('notifDot');
    const notifList = document.getElementById('notifDropdownList');

    if (notifBadge) {
      let count = parseInt(notifBadge.textContent) || 0;
      count = Math.max(0, count - 1);
      if (count > 0) {
        notifBadge.textContent = count > 99 ? '99+' : count;
      } else {
        notifBadge.classList.add('d-none');
        if (notifDot) notifDot.classList.add('d-none');
      }
    }

    if (notifList && notifList.children.length === 0) {
      notifList.innerHTML = '<div class="text-center py-4 text-muted small"><i class="bi bi-bell-slash d-block mb-1 fs-5"></i>No unread notifications</div>';
    }

    // Persist mark as read on server
    fetch('/api/notifications/' + notifId + '/read', { method: 'POST' })
      .then(() => {
        if (targetUrl && targetUrl !== '#' && targetUrl !== 'javascript:void(0)') {
          window.location.href = targetUrl;
        } else {
          fetchNotifications();
        }
      });
  };

  window.markAllNotificationsRead = function(event) {
    if (event) event.preventDefault();
    fetch('/api/notifications/read-all', { method: 'POST' })
      .then(() => fetchNotifications());
  };

  // Habit Tracker Attendance Calendar Hover Tooltip Handler
  document.addEventListener('DOMContentLoaded', () => {
    let tooltipEl = document.getElementById('habitCalendarTooltip');
    if (!tooltipEl) {
      tooltipEl = document.createElement('div');
      tooltipEl.id = 'habitCalendarTooltip';
      tooltipEl.className = 'habit-calendar-tooltip';
      document.body.appendChild(tooltipEl);
    }

    function showTooltip(e, cell) {
      if (cell.classList.contains('empty')) return;

      const date = cell.getAttribute('data-date') || '';
      const weekday = cell.getAttribute('data-weekday') || '';
      const status = cell.getAttribute('data-status') || 'N/A';
      const punchin = cell.getAttribute('data-punchin') || '-';
      const punchout = cell.getAttribute('data-punchout') || '-';
      const hours = cell.getAttribute('data-hours') || '-';
      const notes = cell.getAttribute('data-notes') || 'None';

      let statusClass = 'future';
      const lowerStatus = status.toLowerCase();
      if (lowerStatus.includes('present')) statusClass = 'present';
      else if (lowerStatus.includes('absent')) statusClass = 'absent';
      else if (lowerStatus.includes('leave')) statusClass = 'leave';
      else if (lowerStatus.includes('holiday')) statusClass = 'holiday';
      else if (lowerStatus.includes('weekend')) statusClass = 'weekend';

      tooltipEl.innerHTML = `
        <div class="habit-tooltip-header">
          <span class="habit-tooltip-date">${escapeHtml(date)} (${escapeHtml(weekday)})</span>
          <span class="habit-tooltip-status status-${statusClass}">${escapeHtml(status)}</span>
        </div>
        <div class="habit-tooltip-body">
          <div class="habit-tooltip-row">
            <span class="label"><i class="bi bi-box-arrow-in-right me-1 text-success"></i>Punch In</span>
            <span class="val">${escapeHtml(punchin || '-')}</span>
          </div>
          <div class="habit-tooltip-row">
            <span class="label"><i class="bi bi-box-arrow-right me-1 text-danger"></i>Punch Out</span>
            <span class="val">${escapeHtml(punchout || '-')}</span>
          </div>
          <div class="habit-tooltip-row">
            <span class="label"><i class="bi bi-clock me-1 text-primary"></i>Working Hours</span>
            <span class="val">${escapeHtml(hours || '-')}</span>
          </div>
          <div class="habit-tooltip-row">
            <span class="label"><i class="bi bi-journal-text me-1 text-warning"></i>Notes</span>
            <span class="val">${escapeHtml(notes || 'None')}</span>
          </div>
        </div>
      `;

      tooltipEl.classList.add('visible');
      positionTooltip(e, cell);
    }

    function positionTooltip(e, cell) {
      if (!tooltipEl.classList.contains('visible')) return;
      const rect = cell.getBoundingClientRect();
      const tooltipWidth = 250;
      const tooltipHeight = tooltipEl.offsetHeight || 160;

      let left = rect.left + rect.width / 2 - tooltipWidth / 2;
      let top = rect.top - tooltipHeight - 10;

      if (top < 10) {
        top = rect.bottom + 10;
      }
      if (left < 10) left = 10;
      if (left + tooltipWidth > window.innerWidth - 10) {
        left = window.innerWidth - tooltipWidth - 10;
      }

      tooltipEl.style.left = `${left}px`;
      tooltipEl.style.top = `${top}px`;
    }

    function hideTooltip() {
      tooltipEl.classList.remove('visible');
    }

    document.addEventListener('mouseover', (e) => {
      const cell = e.target.closest('.calendar-day-cell');
      if (cell && !cell.classList.contains('empty')) {
        showTooltip(e, cell);
      }
    });

    document.addEventListener('mouseout', (e) => {
      const cell = e.target.closest('.calendar-day-cell');
      if (cell) {
        hideTooltip();
      }
    });

    document.addEventListener('mousemove', (e) => {
      const cell = e.target.closest('.calendar-day-cell');
      if (cell && tooltipEl.classList.contains('visible')) {
        positionTooltip(e, cell);
      }
    });
  });
})();
// cache refresh 
