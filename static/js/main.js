document.addEventListener('submit', function (event) {
  const form = event.target;
  if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) { event.preventDefault(); return; }
  if (!event.defaultPrevented) { const button = form.querySelector('button[type="submit"], button:not([type])'); if (button && !button.name) { button.disabled = true; button.textContent = 'Working…'; } }
});
