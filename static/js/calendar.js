/* The reminders calendar on the left of every page.
   Tap a day to see what's on. Arrow keys move between days. */
(function () {
    'use strict';

    const tab = document.querySelector('[data-cal-tab]');
    const panel = document.querySelector('[data-cal-panel]');
    if (!tab || !panel) {
        return;
    }
    const body = panel.querySelector('[data-cal-body]');
    const title = panel.querySelector('[data-cal-title]');
    const dayBox = panel.querySelector('[data-cal-day]');
    const STORE_KEY = 'appwheel-calendar-open';
    const KIND_COLOUR = {
        trial: 'red', charge_check: 'red', renewal: 'amber',
        appointment: 'blue', prescription: 'blue', privacy: 'purple', other: 'purple'
    };
    const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
        'August', 'September', 'October', 'November', 'December'];
    const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

    let data = null;
    let shown = null;      // first day of the month on screen
    let selected = null;   // 'YYYY-MM-DD'

    tab.setAttribute('role', 'button');
    tab.setAttribute('aria-expanded', 'false');

    function iso(day) {
        return day.getFullYear() + '-' + String(day.getMonth() + 1).padStart(2, '0') + '-' + String(day.getDate()).padStart(2, '0');
    }

    function fromIso(text) {
        const parts = text.split('-').map(Number);
        return new Date(parts[0], parts[1] - 1, parts[2]);
    }

    function niceDay(text) {
        const day = fromIso(text);
        return DAYS[day.getDay()] + ' ' + day.getDate() + ' ' + MONTHS[day.getMonth()];
    }

    function escapeHtml(text) {
        const span = document.createElement('span');
        span.textContent = text;
        return span.innerHTML;
    }

    function remember(open) {
        try { sessionStorage.setItem(STORE_KEY, open ? '1' : '0'); } catch (error) { /* private browsing */ }
    }

    function wasOpen() {
        try { return sessionStorage.getItem(STORE_KEY) === '1'; } catch (error) { return false; }
    }

    function setOpen(open, moveFocus) {
        if (open) {
            /* Only one side panel at a time, so they don't cover each other on a phone */
            document.dispatchEvent(new CustomEvent('appwheel:panel-open', { detail: 'calendar' }));
        }
        panel.classList.toggle('is-open', open);
        document.body.classList.toggle('cal-is-open', open);
        tab.setAttribute('aria-expanded', open ? 'true' : 'false');
        remember(open);
        if (open && !data) {
            load(null);
        }
        if (moveFocus) {
            if (open) {
                const focusDay = body.querySelector('[aria-pressed="true"]') || panel.querySelector('[data-cal-today]');
                focusDay.focus();
            } else {
                tab.focus();
            }
        }
    }

    document.addEventListener('appwheel:panel-open', function (event) {
        if (event.detail !== 'calendar' && panel.classList.contains('is-open')) {
            setOpen(false, false);
        }
    });

    function load(month, focusAfter) {
        const url = panel.dataset.calUrl + (month ? '?month=' + month : '');
        return fetch(url, { credentials: 'same-origin', headers: { 'X-Requested-With': 'fetch' } })
            .then(function (response) { return response.json(); })
            .then(function (json) {
                data = json;
                shown = fromIso(json.month + '-01');
                if (!selected || selected.slice(0, 7) !== json.month) {
                    selected = json.today.slice(0, 7) === json.month ? json.today : json.month + '-01';
                }
                draw();
                if (focusAfter) {
                    focusAfter();
                }
            })
            .catch(function () {
                title.textContent = 'Couldn\'t load your reminders';
            });
    }

    function draw() {
        title.textContent = data.title;
        const firstWeekday = (shown.getDay() + 6) % 7;   // Monday first
        const start = new Date(shown.getFullYear(), shown.getMonth(), 1 - firstWeekday);
        let html = '';
        for (let week = 0; week < 6; week++) {
            html += '<tr>';
            for (let weekday = 0; weekday < 7; weekday++) {
                const day = new Date(start.getFullYear(), start.getMonth(), start.getDate() + week * 7 + weekday);
                const key = iso(day);
                const items = data.days[key] || [];
                const waiting = items.filter(function (item) { return !item.done; });
                const classes = ['cal-day-button'];
                if (day.getMonth() !== shown.getMonth()) { classes.push('is-other-month'); }
                if (key === data.today) { classes.push('is-today'); }
                const dots = waiting.slice(0, 3).map(function (item) {
                    return '<span class="kind-dot kind-dot-' + (KIND_COLOUR[item.kind] || 'purple') + '"></span>';
                }).join('');
                const label = niceDay(key) + (key === data.today ? ', today' : '') +
                    (waiting.length ? ', ' + waiting.length + ' reminder' + (waiting.length > 1 ? 's' : '') : '');
                html += '<td><button type="button" class="' + classes.join(' ') + '" data-day="' + key + '"' +
                    ' aria-pressed="' + (key === selected ? 'true' : 'false') + '" aria-label="' + label + '"' +
                    ' tabindex="' + (key === selected ? '0' : '-1') + '">' +
                    '<span aria-hidden="true">' + day.getDate() + '</span><span class="cal-dots" aria-hidden="true">' + dots + '</span></button></td>';
            }
            html += '</tr>';
        }
        body.innerHTML = html;
        showDay();
    }

    function showDay() {
        const items = data.days[selected] || [];
        let html = '<h3>' + escapeHtml(niceDay(selected)) + (selected === data.today ? ' (today)' : '') + '</h3>';
        if (items.length) {
            html += '<ul class="cal-items">' + items.map(function (item) {
                return '<li class="kind-' + item.kind + (item.done ? ' is-done' : '') + '">' +
                    '<span class="kind-dot kind-dot-' + (KIND_COLOUR[item.kind] || 'purple') + '" aria-hidden="true"></span>' +
                    '<span><a href="' + item.url + '">' + escapeHtml(item.title) + '</a>' +
                    '<span class="cal-item-meta">' + (item.time ? escapeHtml(item.time) + ' · ' : '') + escapeHtml(item.kind_label) +
                    (item.done ? ' · done' : '') + '</span></span></li>';
            }).join('') + '</ul>';
        } else {
            html += '<p class="todo-hint">Nothing on this day.</p>';
        }
        html += '<p><a class="button button-small button-secondary" href="' + data.add_url + '?kind=other&amp;date=' + selected + '">Add a reminder for this day</a></p>';
        dayBox.innerHTML = html;
    }

    function choose(key, moveFocus) {
        if (key.slice(0, 7) !== data.month) {
            selected = key;
            load(key.slice(0, 7), function () { focusSelected(moveFocus); });
            return;
        }
        selected = key;
        body.querySelectorAll('[data-day]').forEach(function (button) {
            const on = button.dataset.day === key;
            button.setAttribute('aria-pressed', on ? 'true' : 'false');
            button.tabIndex = on ? 0 : -1;
        });
        showDay();
        focusSelected(moveFocus);
    }

    function focusSelected(moveFocus) {
        if (moveFocus) {
            const button = body.querySelector('[data-day="' + selected + '"]');
            if (button) { button.focus(); }
        }
    }

    function changeMonth(step) {
        const next = new Date(shown.getFullYear(), shown.getMonth() + step, 1);
        selected = null;
        load(iso(next).slice(0, 7));
    }

    tab.addEventListener('click', function (event) {
        event.preventDefault();
        setOpen(!panel.classList.contains('is-open'), true);
    });
    panel.querySelector('[data-cal-close]').addEventListener('click', function (event) {
        event.preventDefault();
        setOpen(false, true);
    });
    panel.querySelector('[data-cal-prev]').addEventListener('click', function () { changeMonth(-1); });
    panel.querySelector('[data-cal-next]').addEventListener('click', function () { changeMonth(1); });
    panel.querySelector('[data-cal-today]').addEventListener('click', function () {
        selected = null;
        load(null, function () { focusSelected(true); });
    });

    body.addEventListener('click', function (event) {
        const button = event.target.closest('[data-day]');
        if (button) {
            choose(button.dataset.day, false);
        }
    });

    body.addEventListener('keydown', function (event) {
        const moves = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 };
        if (!(event.key in moves) || !selected) {
            return;
        }
        event.preventDefault();
        const day = fromIso(selected);
        day.setDate(day.getDate() + moves[event.key]);
        choose(iso(day), true);
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && panel.classList.contains('is-open') && !document.querySelector('dialog[open]')) {
            setOpen(false, true);
        }
    });

    if (wasOpen()) {
        panel.classList.add('no-slide');
        setOpen(true, false);
        requestAnimationFrame(function () { panel.classList.remove('no-slide'); });
    }
}());
