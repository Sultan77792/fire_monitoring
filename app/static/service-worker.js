// Имя кэша и версия
const CACHE_NAME = 'forest-fires-cache-v2';
const API_CACHE_NAME = 'forest-fires-api-cache-v2';

// Ресурсы для кэширования при установке (статические файлы)
const urlsToCache = [
    '/',
    '/fires',
    '/analytics',
    '/logs',
    '/summary',
    '/login',
    '/manifest.json',
    '/static/icon-192.png',
    '/static/icon-512.png',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    'https://cdn.jsdelivr.net/npm/chart.js',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
    '/socket.io/socket.io.js'
];

// Установка Service Worker и кэширование статических ресурсов
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Caching static resources');
                return cache.addAll(urlsToCache);
            })
            .then(() => self.skipWaiting()) // Активируем SW сразу после установки
            .catch(err => console.error('Cache addAll failed:', err))
    );
});

// Активация Service Worker и очистка старых кэшей
self.addEventListener('activate', event => {
    const cacheWhitelist = [CACHE_NAME, API_CACHE_NAME];
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (!cacheWhitelist.includes(cacheName)) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
        .then(() => self.clients.claim()) // Захватываем контроль над клиентами сразу
    );
});

// Обработка запросов
self.addEventListener('fetch', event => {
    const requestUrl = new URL(event.request.url);

    // Стратегия для API-запросов (Cache then network с фоновой синхронизацией)
    if (requestUrl.pathname.startsWith('/api/')) {
        event.respondWith(
            caches.match(event.request)
                .then(cachedResponse => {
                    const networkFetch = fetch(event.request)
                        .then(response => {
                            // Кэшируем только успешные GET-запросы
                            if (response.ok && event.request.method === 'GET') {
                                const responseToCache = response.clone();
                                caches.open(API_CACHE_NAME)
                                    .then(cache => cache.put(event.request, responseToCache));
                            }
                            return response;
                        })
                        .catch(() => {
                            // Если сеть недоступна и кэш есть, возвращаем кэш
                            if (cachedResponse) return cachedResponse;
                            throw new Error('Network unavailable and no cache');
                        });

                    // Возвращаем кэш сразу, если он есть, и обновляем в фоне
                    return cachedResponse || networkFetch;
                })
                .catch(() => {
                    return new Response(JSON.stringify({ error: 'Оффлайн: данные недоступны' }), {
                        status: 503,
                        headers: { 'Content-Type': 'application/json' }
                    });
                })
        );

        // Фоновая синхронизация для POST-запросов, если оффлайн
        if (event.request.method === 'POST') {
            event.waitUntil(
                fetch(event.request).catch(() => {
                    self.registration.sync.register('sync-fires')
                        .then(() => console.log('Background sync registered for POST request'));
                })
            );
        }
    } 
    // Стратегия для статических ресурсов (Cache first)
    else {
        event.respondWith(
            caches.match(event.request)
                .then(response => {
                    if (response) return response;
                    return fetch(event.request)
                        .then(networkResponse => {
                            if (!networkResponse || networkResponse.status !== 200 || networkResponse.type !== 'basic') {
                                return networkResponse;
                            }
                            const responseToCache = networkResponse.clone();
                            caches.open(CACHE_NAME)
                                .then(cache => cache.put(event.request, responseToCache));
                            return networkResponse;
                        })
                        .catch(() => {
                            return new Response('Оффлайн-режим: страница недоступна', {
                                headers: { 'Content-Type': 'text/plain' }
                            });
                        });
                })
        );
    }
});

// Фоновая синхронизация для отправки отложенных POST-запросов
self.addEventListener('sync', event => {
    if (event.tag === 'sync-fires') {
        event.waitUntil(
            syncPendingRequests()
        );
    }
});

async function syncPendingRequests() {
    // Здесь можно добавить логику для хранения и повторной отправки POST-запросов
    // Например, использовать IndexedDB для сохранения запросов
    console.log('Background sync triggered');
    const clients = await self.clients.matchAll();
    clients.forEach(client => {
        client.postMessage({ type: 'sync-complete', message: 'Данные синхронизированы' });
    });
}

// Обработка push-уведомлений (если сервер отправляет уведомления)
self.addEventListener('push', event => {
    const data = event.data ? event.data.json() : { title: 'Обновление', body: 'Данные обновлены' };
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/static/icon-192.png',
            badge: '/static/icon-192.png',
            data: { url: data.url || '/fires' }
        })
    );
});

// Обработка клика по уведомлению
self.addEventListener('notificationclick', event => {
    event.notification.close();
    event.waitUntil(
        clients.openWindow(event.notification.data.url)
    );
});

// Сообщения от клиентов
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'CHECK_UPDATE') {
        event.waitUntil(
            checkForUpdate(event.source)
        );
    }
});

async function checkForUpdate(client) {
    try {
        const response = await fetch('/api/version'); // Предполагаемый эндпоинт для проверки версии
        const data = await response.json();
        if (data.version !== CACHE_NAME) {
            client.postMessage({ type: 'UPDATE_AVAILABLE', version: data.version });
        }
    } catch (error) {
        console.error('Error checking for update:', error);
    }
}