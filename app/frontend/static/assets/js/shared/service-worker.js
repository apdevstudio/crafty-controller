// This is the "Offline page" service worker

importScripts(
	"https://storage.googleapis.com/workbox-cdn/releases/5.1.2/workbox-sw.js"
);

const CACHE = "crafty-controller";

//This service worker is basically just here to make browsers
//accept the PWA. It's not doing much anymore

// TODO: replace the following with the correct offline fallback page i.e.: const offlineFallbackPage = "offline.html";
const offlineFallbackPage = "/offline";

// self.addEventListener("message", (event) => {
// 	console.log(event.data);
// 	if (event.data && event.data.type === "SKIP_WAITING") {
// 		self.skipWaiting();
// 	}
// });

if (workbox.navigationPreload.isSupported()) {
	workbox.navigationPreload.enable();
}

// self.addEventListener('fetch', (event) => {
//   if (event.request.mode === 'navigate') {
//     event.respondWith((async () => {
//       try {
//         const preloadResp = await event.preloadResponse;

//         if (preloadResp) {
//           return preloadResp;
//         }
//         const networkResp = await fetch(event.request);
//         return networkResp;
//       } catch (error) {

//         const cache = await caches.open(CACHE);
//         const cachedResp = await cache.match(offlineFallbackPage);
//         return cachedResp;
//       }
//     })());
//   }
// });
