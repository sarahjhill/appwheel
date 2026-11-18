/* AppWheel service worker.
   Privacy first: only the design files (styles, scripts, icons) and the offline
   page are saved on the phone. Your apps, reminders and care diary are never
   saved on the device, so nothing private is left on a shared or lost phone. */
const CACHE = 'appwheel-v3';
const FILES = [{% for file in files %}'{{ file }}'{% if not forloop.last %}, {% endif %}{% endfor %}];
const OFFLINE_URL = '{{ offline_url }}';

self.addEventListener('install', function (event) {
    event.waitUntil(caches.open(CACHE).then(function (cache) { return cache.addAll(FILES); }));
    self.skipWaiting();
});

self.addEventListener('activate', function (event) {
    event.waitUntil(
        caches.keys().then(function (names) {
            return Promise.all(names.filter(function (name) { return name !== CACHE; })
                .map(function (name) { return caches.delete(name); }));
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', function (event) {
    const request = event.request;
    if (request.method !== 'GET') {
        return;
    }
    const url = new URL(request.url);

    // Pages: always fetch fresh from the internet; if there's no signal, show the offline page
    if (request.mode === 'navigate') {
        event.respondWith(fetch(request).catch(function () { return caches.match(OFFLINE_URL); }));
        return;
    }

    // Design files: always get the latest version, and keep a copy for when there's no signal.
    // (Using the saved copy first would show old styles after AppWheel is updated.)
    if (url.origin === self.location.origin && url.pathname.startsWith('/static/')) {
        event.respondWith(
            // 'no-cache' makes the browser check with the server, so it never uses an old copy
            fetch(request, { cache: 'no-cache' }).then(function (response) {
                if (response.ok) {
                    const copy = response.clone();
                    caches.open(CACHE).then(function (cache) { cache.put(request, copy); });
                }
                return response;
            }).catch(function () { return caches.match(request); })
        );
    }
});
