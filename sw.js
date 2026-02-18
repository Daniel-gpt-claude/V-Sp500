const CACHE = 'sp500-screener-v1';
const ASSETS = ['./','./index.html','./styles.css','./app.js','./manifest.json','./data/sp500_momentum.json'];
self.addEventListener('install', (e) => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS))); });
self.addEventListener('fetch', (e) => {
  e.respondWith(caches.match(e.request).then(r => r || fetch(e.request).then(res => {
    const copy = res.clone();
    caches.open(CACHE).then(c => c.put(e.request, copy));
    return res;
  }).catch(() => r)));
});
