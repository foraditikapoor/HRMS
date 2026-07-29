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

  // Fallback and instant toggle handling for collapse dropdowns
  document.addEventListener('DOMContentLoaded', () => {
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
  });
})();
