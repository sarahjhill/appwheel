/* Lets AppWheel be installed on a phone, and shows an "Install" button where the browser allows it. */
(function () {
    'use strict';

    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function () {
            navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(function () {
                /* Not available (for example over plain http): AppWheel still works as a website. */
            });
        });
    }

    let installPrompt = null;
    const installButton = document.querySelector('[data-install]');

    window.addEventListener('beforeinstallprompt', function (event) {
        event.preventDefault();
        installPrompt = event;
        if (installButton) {
            installButton.hidden = false;
        }
    });

    if (installButton) {
        installButton.addEventListener('click', function () {
            if (!installPrompt) {
                return;
            }
            installPrompt.prompt();
            installPrompt.userChoice.finally(function () {
                installPrompt = null;
                installButton.hidden = true;
            });
        });
    }
}());
