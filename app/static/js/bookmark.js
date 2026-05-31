// Переключение «избранное / изучено» без перезагрузки страницы.
(function () {
    function updateButton(role, isOn) {
        const btn = document.querySelector('button[data-role="' + role + '"]');
        if (!btn) return;
        const cfg = {
            favorite: { on: '★ В избранном', off: '☆ В избранное', cls: 'btn-primary' },
            studied:  { on: '✓ Изучено',     off: 'Отметить изученным', cls: 'btn-success' },
        }[role];
        btn.textContent = isOn ? cfg.on : cfg.off;
        btn.classList.toggle(cfg.cls, isOn);
        btn.classList.toggle('btn-ghost', !isOn);
    }

    document.querySelectorAll('form.ajax-toggle').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            const btn = form.querySelector('button');
            btn.disabled = true;
            fetch(form.action, {
                method: 'POST',
                headers: { 'X-Requested-With': 'fetch' },
            })
                .then(function (r) {
                    if (!r.ok) throw new Error('request failed');
                    return r.json();
                })
                .then(function (data) {
                    updateButton('favorite', data.is_favorite);
                    updateButton('studied', data.is_studied);
                })
                .catch(function () {
                    form.submit(); // фолбэк: обычная отправка
                })
                .finally(function () {
                    btn.disabled = false;
                });
        });
    });
})();
