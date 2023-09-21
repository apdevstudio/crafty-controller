// This is the "Offline page" service worker

importScripts(
	"https://storage.googleapis.com/workbox-cdn/releases/5.1.2/workbox-sw.js"
);

const CACHE = "crafty-controller";

//This service worker is basically just here to make browsers
//accept the PWA. It's not doing much anymore

if (workbox.navigationPreload.isSupported()) {
	workbox.navigationPreload.enable();
}
