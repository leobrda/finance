const CACHE_NAME = 'fin-finance-v2';
const STATIC_ASSETS = [
  'https://cdn.tailwindcss.com',
  'https://unpkg.com/lucide@latest',
  'https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700;900&display=swap'
];

// Instalação do Service Worker
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Ativação e limpeza imediata dos caches antigos (v1)
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Interceptação de requisições
self.addEventListener('fetch', (event) => {
  const req = event.request;

  // 1. NUNCA interceptar páginas HTML, navegação, requisições POST ou APIs do Django
  // Isso impede 100% que ocorra tela branca por cache quebrado
  if (req.mode === 'navigate' || req.method !== 'GET' || req.url.includes('/admin/') || req.url.includes('/api/')) {
    return;
  }

  // 2. Apenas recursos estáticos (fontes, scripts CDN, ícones) usam cache com fallback de rede
  event.respondWith(
    caches.match(req).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(req);
    }).catch(() => {
      return fetch(req);
    })
  );
});

// ==========================================
// NOTIFICAÇÕES WEB PUSH (PWA)
// ==========================================
self.addEventListener('push', function(event) {
  if (!event.data) return;

  let data = {};
  try {
    data = event.data.json();
  } catch (e) {
    data = { title: 'FIN. FINANCE', body: event.data.text() };
  }

  const options = {
    body: data.body || 'Você tem notificações no FIN. FINANCE.',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/icon-192x192.png',
    vibrate: [100, 50, 100],
    data: {
      url: data.url || '/dashboard/'
    }
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'FIN. FINANCE', options)
  );
});

// Ao clicar na notificação, foca ou abre a tela no telemóvel
self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  const targetUrl = event.notification.data ? event.notification.data.url : '/dashboard/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes('/dashboard/') && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});