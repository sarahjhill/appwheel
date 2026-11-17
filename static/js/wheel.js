/* The App Wheel: spin, turn and tap apps to see their details. */
(function () {
    'use strict';

    const wheel = document.querySelector('[data-wheel]');
    if (!wheel) {
        return;
    }

    const apps = Array.from(wheel.querySelectorAll('.wheel-app'));
    const count = apps.length;
    const step = 360 / count;
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const spinTime = reduceMotion ? 0 : 1400;

    const centre = wheel.querySelector('[data-centre]');
    const centreName = wheel.querySelector('[data-centre-name]');
    const centrePrice = wheel.querySelector('[data-centre-price]');
    const centrePill = wheel.querySelector('[data-centre-pill]');

    let rotation = 0;
    let selected = 0;
    let spinTimer = null;

    function mod(number, size) {
        return ((number % size) + size) % size;
    }

    /* Turn the wheel to an angle. The app at the top becomes the selected one. */
    function rotateTo(degrees, spinning) {
        rotation = degrees;
        wheel.classList.toggle('is-spinning', Boolean(spinning));
        wheel.style.setProperty('--rot', rotation + 'deg');
        selected = mod(Math.round(-rotation / step), count);

        clearTimeout(spinTimer);
        if (spinning) {
            apps.forEach(function (app) { app.classList.remove('is-selected'); });
            spinTimer = setTimeout(function () {
                wheel.classList.remove('is-spinning');
                showSelected();
            }, spinTime);
        } else {
            showSelected();
        }
    }

    /* Show the selected app in the middle of the wheel. */
    function showSelected() {
        const app = apps[selected];
        apps.forEach(function (other) { other.classList.toggle('is-selected', other === app); });
        centreName.textContent = app.dataset.name;
        centrePrice.textContent = app.dataset.price;
        centrePill.textContent = app.dataset.label;
        centrePill.className = 'centre-pill badge-' + app.dataset.light;
    }

    /* Bring one app to the top by the shortest way round. */
    function bringToTop(index) {
        const target = -index * step;
        const turns = Math.round((rotation - target) / 360);
        rotateTo(target + 360 * turns, false);
    }

    function turn(direction) {
        rotateTo(rotation - step * direction, false);
    }

    function spin() {
        const extra = 1 + Math.floor(Math.random() * Math.max(count - 1, 1));
        rotateTo(rotation + (reduceMotion ? 0 : 720) + step * extra, true);
    }

    function openCard(index) {
        const card = document.getElementById(apps[index].dataset.card);
        if (card && typeof card.showModal === 'function') {
            card.showModal();
        } else {
            window.location.href = '/apps/';  // very old browsers: show the list instead
        }
    }

    apps.forEach(function (app, index) {
        app.addEventListener('click', function () {
            bringToTop(index);
            openCard(index);
        });
    });

    centre.addEventListener('click', function () {
        openCard(selected);
    });

    document.querySelectorAll('[data-turn]').forEach(function (button) {
        button.addEventListener('click', function () {
            turn(Number(button.dataset.turn));
        });
    });

    document.querySelector('[data-spin]').addEventListener('click', spin);

    /* Left and right arrow keys turn the wheel when it has focus. */
    wheel.addEventListener('keydown', function (event) {
        if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
            event.preventDefault();
            turn(event.key === 'ArrowRight' ? 1 : -1);
            apps[selected].focus();
        }
    });

    /* Clicking the dark area around an app card closes it. */
    document.querySelectorAll('dialog.app-card').forEach(function (card) {
        card.addEventListener('click', function (event) {
            if (event.target === card) {
                card.close();
            }
        });
    });

    showSelected();
}());
