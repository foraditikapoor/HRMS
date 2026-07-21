(() => {
  const sidebar = document.getElementById('appSidebar');
  const toggle = document.querySelector('.sidebar-toggle');
  if (!sidebar || !toggle) return;
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
})();
