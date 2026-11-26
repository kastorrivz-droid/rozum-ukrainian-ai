(() => {
  'use strict';

  // Public, non-secret runtime configuration. Never place provider keys here.
  globalThis.ROZUMAssistantConfig = Object.freeze({
    apiEnabled: true,
    apiBaseUrl: 'https://rozum-reeves-api.rozum-reeves-worker.workers.dev',
    requestTimeoutMs: 25000,
    webSearchEnabled: false
  });
})();
