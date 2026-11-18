/* The to-do panel on the right of every page.
   Add, tick, edit and delete to-dos without leaving the page you're on. */
(function () {
    'use strict';

    const tab = document.querySelector('[data-todo-tab]');
    const panel = document.querySelector('[data-todo-panel]');
    if (!tab || !panel) {
        return;
    }
    const list = panel.querySelector('[data-todo-list]');
    const status = panel.querySelector('[data-todo-status]');
    const badge = tab.querySelector('[data-todo-badge]');
    const newInput = panel.querySelector('#todo-new');
    const STORE_KEY = 'appwheel-todo-open';

    /* The tab works like a button once JavaScript is running */
    tab.setAttribute('role', 'button');
    tab.setAttribute('aria-expanded', 'false');

    function remember(open) {
        try { sessionStorage.setItem(STORE_KEY, open ? '1' : '0'); } catch (error) { /* private browsing */ }
    }

    function wasOpen() {
        try { return sessionStorage.getItem(STORE_KEY) === '1'; } catch (error) { return false; }
    }

    function setOpen(open, moveFocus) {
        panel.classList.toggle('is-open', open);
        document.body.classList.toggle('todo-is-open', open);
        tab.setAttribute('aria-expanded', open ? 'true' : 'false');
        remember(open);
        if (moveFocus) {
            (open ? newInput : tab).focus();
        }
    }

    tab.addEventListener('click', function (event) {
        event.preventDefault();
        setOpen(!panel.classList.contains('is-open'), true);
    });

    panel.querySelector('[data-todo-close]').addEventListener('click', function (event) {
        event.preventDefault();
        setOpen(false, true);
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' && panel.classList.contains('is-open') && !document.querySelector('dialog[open]')) {
            setOpen(false, true);
        }
    });

    /* Keep the panel open while moving between pages, if it was open */
    if (wasOpen()) {
        panel.classList.add('no-slide');
        setOpen(true, false);
        requestAnimationFrame(function () { panel.classList.remove('no-slide'); });
    }

    function refresh(html, focusAfter) {
        list.innerHTML = html;
        const wrapper = list.firstElementChild;
        const count = Number(wrapper.dataset.todoCount || 0);
        badge.hidden = count === 0;
        badge.firstChild.nodeValue = String(count);
        status.textContent = wrapper.dataset.todoAnnounce || '';
        if (focusAfter) {
            focusAfter();
        }
    }

    /* Send every to-do form in the background and swap in the new list */
    panel.addEventListener('submit', function (event) {
        const form = event.target.closest('[data-todo-form]');
        if (!form) {
            return;
        }
        event.preventDefault();
        const isAdd = form.hasAttribute('data-todo-add');
        if (isAdd && !newInput.value.trim()) {
            newInput.focus();
            return;
        }
        fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            headers: { 'X-Requested-With': 'fetch' },
            credentials: 'same-origin'
        }).then(function (response) {
            if (!response.ok) {
                throw new Error('Not saved');
            }
            return response.text();
        }).then(function (html) {
            refresh(html, function () {
                if (isAdd) {
                    newInput.value = '';
                }
                newInput.focus();
            });
        }).catch(function () {
            status.textContent = 'That didn\'t save. Check your connection and try again.';
        });
    });

    /* Edit in place */
    panel.addEventListener('click', function (event) {
        const editLink = event.target.closest('[data-todo-edit]');
        const cancel = event.target.closest('[data-todo-cancel]');
        if (editLink) {
            event.preventDefault();
            const item = editLink.closest('[data-todo-item]');
            item.classList.add('is-editing');
            item.querySelector('[data-todo-edit-form]').hidden = false;
            const input = item.querySelector('[data-todo-edit-form] input[name="text"]');
            input.focus();
            input.select();
        }
        if (cancel) {
            const item = cancel.closest('[data-todo-item]');
            item.classList.remove('is-editing');
            item.querySelector('[data-todo-edit-form]').hidden = true;
            item.querySelector('[data-todo-edit]').focus();
        }
    });
}());
