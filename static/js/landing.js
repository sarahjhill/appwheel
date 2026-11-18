/* The example wheel on the homepage. It only moves when someone presses Spin or taps an app. */
(function () {
    'use strict';

    const wheel = document.querySelector('[data-demo-wheel]');
    if (!wheel) {
        return;
    }
    const apps = Array.from(wheel.querySelectorAll('[data-demo-app]'));
    const step = 360 / apps.length;
    const still = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const symbols = { green: '✓', amber: '!', red: '✕' };
    const show = {
        name: document.querySelector('[data-demo-name]'),
        price: document.querySelector('[data-demo-price]'),
        light: document.querySelector('[data-demo-light]'),
        symbol: document.querySelector('[data-demo-symbol]'),
        label: document.querySelector('[data-demo-label]'),
        tip: document.querySelector('[data-demo-tip]')
    };
    let rotation = 0;
    let timer = null;

    function choose(index) {
        const app = apps[index];
        apps.forEach(function (other) { other.classList.toggle('is-selected', other === app); });
        show.name.textContent = app.dataset.name;
        show.price.textContent = app.dataset.price;
        show.light.className = 'light light-' + app.dataset.light;
        show.symbol.textContent = symbols[app.dataset.light];
        show.label.textContent = app.dataset.name + ': ' + app.dataset.label;
        show.tip.textContent = app.dataset.tip;
    }

    function turnTo(degrees, slow) {
        rotation = degrees;
        wheel.classList.toggle('is-spinning', Boolean(slow));
        wheel.style.setProperty('--rot', rotation + 'deg');
        const index = ((Math.round(-rotation / step) % apps.length) + apps.length) % apps.length;
        clearTimeout(timer);
        timer = setTimeout(function () { choose(index); }, still ? 0 : (slow ? 1300 : 450));
    }

    apps.forEach(function (app, index) {
        app.addEventListener('click', function () {
            const target = -index * step;
            turnTo(target + 360 * Math.round((rotation - target) / 360), false);
        });
    });

    document.querySelector('[data-demo-spin]').addEventListener('click', function () {
        const extra = 1 + Math.floor(Math.random() * (apps.length - 1));
        turnTo(rotation - (still ? 0 : 720) - step * extra, true);
    });

    show.label.textContent = apps[0].dataset.name + ': ' + apps[0].dataset.label;
    choose(0);
}());
