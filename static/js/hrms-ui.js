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
})();
