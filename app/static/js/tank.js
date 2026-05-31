// Схема резервуара: адаптивный viewBox + подсветка «точка ↔ легенда».
(function () {
    const svg = document.getElementById('tank-svg');
    const hotspots = document.querySelectorAll('.hotspot');
    const legendItems = document.querySelectorAll('.legend-list li');

    // На узких экранах прячем боковые выноски и приближаем сам резервуар.
    if (svg) {
        const wide = svg.dataset.viewboxWide;
        const narrow = svg.dataset.viewboxNarrow;
        const mq = window.matchMedia('(max-width: 700px)');
        const apply = () => svg.setAttribute('viewBox', mq.matches ? narrow : wide);
        apply();
        mq.addEventListener('change', apply);
    }

    // Подсветка связи точки и пункта легенды.
    function highlight(index, on) {
        if (hotspots[index]) hotspots[index].classList.toggle('is-active', on);
        if (legendItems[index]) legendItems[index].classList.toggle('is-active', on);
    }
    hotspots.forEach((spot, i) => {
        spot.addEventListener('mouseenter', () => highlight(i, true));
        spot.addEventListener('mouseleave', () => highlight(i, false));
    });
    legendItems.forEach((item, i) => {
        item.addEventListener('mouseenter', () => highlight(i, true));
        item.addEventListener('mouseleave', () => highlight(i, false));
    });
})();
