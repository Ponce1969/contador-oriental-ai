'use strict';

/**
 * Service Worker for Contador Oriental
 * Automatically claims clients and purges stale caches on activate to prevent obsolete WebAssembly files.
 */

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      try {
        // Clear all caches to avoid stale wasm/js runtime collisions
        const cacheNames = await caches.keys();
        await Promise.all(
          cacheNames.map((name) => {
            console.log('[SW] Purging cache:', name);
            return caches.delete(name);
          })
        );
      } catch (e) {
        console.warn('[SW] Cache cleanup warning:', e);
      }

      // Immediately take control of all open tabs/clients
      await self.clients.claim();
    })()
  );
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
