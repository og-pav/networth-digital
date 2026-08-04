/* NetWorth Routine — offline shell.
   Bump CACHE whenever index.html or the assets change, so phones pick it up. */
const CACHE = 'nwr-v1';
const CORE = [
  './',
  './index.html',
  './manifest.webmanifest',
  './assets/mark-dark.svg',
  './assets/mark-light.svg',
  './assets/icon-192.png',
  './assets/icon-512.png',
  './assets/apple-touch-icon.png',
  './assets/favicon-32.png'
];

self.addEventListener('install', e=>{
  e.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting()));
});

self.addEventListener('activate', e=>{
  e.waitUntil(
    caches.keys()
      .then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))
      .then(()=>self.clients.claim())
  );
});

self.addEventListener('fetch', e=>{
  const req = e.request;
  if(req.method !== 'GET') return;

  // The page itself: try the network so updates land, fall back to cache offline.
  if(req.mode === 'navigate'){
    e.respondWith(
      fetch(req)
        .then(res=>{
          const copy = res.clone();
          caches.open(CACHE).then(c=>c.put('./index.html', copy));
          return res;
        })
        .catch(()=>caches.match('./index.html').then(r=>r || caches.match('./')))
    );
    return;
  }

  // Everything else: cache first, it never changes without a CACHE bump.
  e.respondWith(
    caches.match(req).then(hit => hit || fetch(req).then(res=>{
      if(res.ok && new URL(req.url).origin === location.origin){
        const copy = res.clone();
        caches.open(CACHE).then(c=>c.put(req, copy));
      }
      return res;
    }))
  );
});
