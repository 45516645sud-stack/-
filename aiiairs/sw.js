// AIIairs: 홈 화면에 추가한 앱. 늘 새 파일을 먼저 받고, 인터넷이 끊기면 마지막으로 본 일정을 보여 준다.
const CACHE = "aiiairs-v1";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icon.svg", "favicon.svg", "img/icon-192.png", "data/fairs.json"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  // 같은 주소의 파일만 다룬다. 놀코(/nolco/)는 놀코의 sw.js 가 맡는다
  if (e.request.method !== "GET" || url.origin !== location.origin || url.pathname.includes("/nolco/")) return;
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        if (res.ok) { const copy = res.clone(); caches.open(CACHE).then((c) => c.put(e.request, copy)); }
        return res;
      })
      .catch(() => caches.match(e.request, { ignoreSearch: true }).then((hit) => hit || Response.error())),
  );
});
