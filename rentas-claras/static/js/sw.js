/**
 * RentasClaras Service Worker
 * Enables PWA installation and basic caching for offline support
 */

const CACHE_NAME = 'rentasclaras-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/static/css/dashboard.css',
  '/static/css/pagos.css',
  '/static/css/login.css',
  '/static/js/state.js',
  '/static/js/pagos.js',
  '/static/js/contratos.js',
  '/static/js/login.js',
  '/static/icon-192.png',
  '/static/icon-512.png',
  '/static/favicon.svg',
  '/static/manifest.json'
];

// Install event - cache essential assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('📦 RentasClaras: Caching app assets');
        return cache.addAll(ASSETS_TO_CACHE);
      })
      .catch((error) => {
        console.log('⚠️ RentasClaras: Some assets failed to cache', error);
      })
  );
  // Activate immediately
  self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  // Take control of all clients immediately
  self.clients.claim();
});

// Fetch event - network first, fallback to cache
self.addEventListener('fetch', (event) => {
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Skip API calls and dynamic content (always fetch fresh)
  const url = new URL(event.request.url);
  if (url.pathname.startsWith('/api/') ||
      url.pathname.startsWith('/pagos') ||
      url.pathname.startsWith('/inquilinos') ||
      url.pathname.startsWith('/contratos') ||
      url.pathname.startsWith('/dashboard')) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        // Cache successful responses for static assets
        if (response.ok && url.pathname.startsWith('/static/')) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        // If network fails, try cache
        return caches.match(event.request);
      })
  );
});
