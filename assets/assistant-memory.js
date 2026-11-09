(() => {
  'use strict';

  const CONSENT_KEY = 'rozum.assistant.memory.consent.v1';
  const HISTORY_KEY = 'rozum.assistant.memory.history.v1';
  const MAX_TURNS = 40;

  function validTurn(turn) {
    const role = turn && (turn.role === 'user' || turn.role === 'assistant') ? turn.role : null;
    const content = String(turn && turn.content || '').trim().slice(0, 4000);
    const at = typeof turn?.at === 'string' ? turn.at : new Date().toISOString();
    return role && content ? { role, content, at } : null;
  }

  function create(options = {}) {
    let storage = options.storage;
    if (storage === undefined) {
      try { storage = globalThis.localStorage; } catch { storage = null; }
    }

    function available() {
      return storage && typeof storage.getItem === 'function' && typeof storage.setItem === 'function';
    }

    function isEnabled() {
      if (!available()) return false;
      try { return storage.getItem(CONSENT_KEY) === 'granted'; } catch { return false; }
    }

    function load() {
      if (!isEnabled()) return [];
      try {
        const parsed = JSON.parse(storage.getItem(HISTORY_KEY) || '[]');
        if (!Array.isArray(parsed)) return [];
        return parsed.flatMap(turn => {
          const cleaned = validTurn(turn);
          return cleaned ? [cleaned] : [];
        }).slice(-MAX_TURNS);
      } catch {
        return [];
      }
    }

    function clear() {
      if (!available()) return;
      try { storage.removeItem(HISTORY_KEY); } catch { /* Storage can be blocked. */ }
    }

    function setConsent(enabled) {
      if (!available()) return false;
      try {
        if (enabled) storage.setItem(CONSENT_KEY, 'granted');
        else {
          storage.removeItem(CONSENT_KEY);
          clear();
        }
        return isEnabled();
      } catch {
        return false;
      }
    }

    function append(turns) {
      if (!isEnabled()) return [];
      const additions = (Array.isArray(turns) ? turns : [turns]).flatMap(turn => {
        const cleaned = validTurn(turn);
        return cleaned ? [cleaned] : [];
      });
      const next = [...load(), ...additions].slice(-MAX_TURNS);
      try { storage.setItem(HISTORY_KEY, JSON.stringify(next)); } catch { return load(); }
      return next;
    }

    return Object.freeze({ isEnabled, setConsent, load, append, clear, maxTurns: MAX_TURNS });
  }

  const api = { create, keys: { consent: CONSENT_KEY, history: HISTORY_KEY } };
  if (typeof globalThis !== 'undefined') globalThis.ROZUMAssistantMemory = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
