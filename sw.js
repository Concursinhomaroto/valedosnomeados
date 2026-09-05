// Service Worker do Vale dos Nomeados — cacheia só o "shell" estático
// (HTML/manifest/ícones). NUNCA intercepta o Firebase Realtime Database:
// os dados em tempo real trafegam por WebSocket, que passa por fora do
// evento 'fetch' de qualquer forma, então a sincronização não é afetada.
const CACHE_NAME = 'vdn-shell-v68';
const PRECACHE_URLS = [
  './',
  './index.html',
  './app/',
  './manifest.json',
  './icons/icon192.png',
  './icons/icon512.png',
  './icons/icon512maskable.png',
  './icons/appletouchicon.png',
  './icons/favicon32.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(names.filter((n) => n !== CACHE_NAME).map((n) => caches.delete(n))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  // Ignora esquemas que a Cache API não suporta (ex.: chrome-extension://,
  // de extensões do navegador injetando suas próprias requisições) — deixa
  // o navegador lidar com elas normalmente, sem passar pelo cache.
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return;
  const isSameOrigin = url.origin === self.location.origin;
  const isAppDoc = req.mode === 'navigate' || url.pathname.endsWith('index.html') || url.pathname.endsWith('/');

  if (isSameOrigin && isAppDoc) {
    // HTML do app: rede primeiro, com o cache só como fallback offline. Cache-first
    // aqui prendia o usuário na versão antiga no carregamento logo após um deploy —
    // a atualização do cache rodava em segundo plano, tarde demais pra afetar a
    // página que já tinha acabado de carregar (só valia a partir do 2º carregamento).
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
          }
          return res;
        })
        .catch(() => caches.match(req))
    );
  } else if (isSameOrigin) {
    // Demais arquivos do shell (ícones, manifest): cache-first, atualizando em segundo plano.
    event.respondWith(
      caches.match(req).then((cached) => {
        const fetchPromise = fetch(req)
          .then((res) => {
            if (res && res.ok) {
              const copy = res.clone();
              caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
            }
            return res;
          })
          .catch(() => cached);
        return cached || fetchPromise;
      })
    );
  } else {
    // CDN externo (SDK do Firebase, Font Awesome): rede primeiro, cache como
    // fallback offline. As chamadas reais de dados do Firebase (wss://) não
    // passam por aqui.
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res && res.ok) {
            const copy = res.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(req, copy));
          }
          return res;
        })
        .catch(() => caches.match(req))
    );
  }
});
