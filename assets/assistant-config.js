(() => {
  'use strict';

  // Public, non-secret runtime configuration. Never place provider keys here.
  globalThis.ROZUMAssistantConfig = Object.freeze({
    apiEnabled: false,
    apiBaseUrl: '',
    requestTimeoutMs: 12000
  });
})();
