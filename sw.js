/* NetWorth Routine — offline shell.
   Bump CACHE whenever index.html or the assets change, so phones pick it up. */
const CACHE = 'nwr-v10';
const CORE = [
  './',
  './index.html',
  './manifest.webmanifest',
  './assets/logo-lockup.svg',
  './assets/logo-lockup-reverse.svg',
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

  // Calendar data: always network first so today's bookings stay fresh.
  if(new URL(req.url).pathname.endsWith('/calendar.json')){
    e.respondWith(fetch(req).catch(()=>caches.match(req)));
    return;
  }

  // The page itself: try the network so updates land, fall back to cache offline.
  // cache:'reload' is the important bit — a plain fetch() can still be answered
  // by the browser's own HTTP cache, which silently pins the app to an old
  // version even after CACHE is bumped here.
  if(req.mode === 'navigate'){
    e.respondWith(
      fetch(new Request(req.url, {cache:'reload', credentials:'same-origin'}))
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
