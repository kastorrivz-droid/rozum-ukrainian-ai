(() => {
  'use strict';

  function safeBaseUrl(value) {
    const raw = String(value || '').trim().replace(/\/+$/, '');
    if (!raw) return '';
    try {
      const parsed = new URL(raw);
      const local = parsed.hostname === '127.0.0.1' || parsed.hostname === 'localhost';
      return parsed.protocol === 'https:' || (parsed.protocol === 'http:' && local) ? parsed.href.replace(/\/+$/, '') : '';
    } catch {
      return '';
    }
  }

  function cleanHistory(history) {
    if (!Array.isArray(history)) return [];
    return history.slice(-12).flatMap(turn => {
      const role = turn && (turn.role === 'user' || turn.role === 'assistant') ? turn.role : null;
      const content = String(turn && turn.content || '').trim().slice(0, 4000);
      return role && content ? [{ role, content }] : [];
    });
  }

  function create(options = {}) {
    const engine = options.engine || globalThis.ROZUMAssistantEngine;
    if (!engine || typeof engine.reply !== 'function') throw new Error('ROZUM assistant engine is required');
    const coreFactory = options.core || globalThis.ROZUMAssistantCore;
    const core = coreFactory && typeof coreFactory.create === 'function' ? coreFactory.create({ engine }) : null;

    const config = options.config || globalThis.ROZUMAssistantConfig || {};
    const baseUrl = safeBaseUrl(config.apiBaseUrl);
    const fetchImpl = options.fetchImpl || globalThis.fetch;
    const isRemoteEnabled = config.apiEnabled === true && Boolean(baseUrl) && typeof fetchImpl === 'function';
    const requestTimeoutMs = Math.max(1000, Math.min(Number(config.requestTimeoutMs) || 12000, 30000));

    async function reply(question, session, history = []) {
      const local = engine.reply(question, session);
      const coreContext = core ? core.classify(local) : null;
      const localResult = { ...local, core: coreContext, transport: 'local', provider: 'local-knowledge' };
      if (!isRemoteEnabled) return localResult;

      const controller = typeof AbortController === 'function' ? new AbortController() : null;
      const timer = controller ? setTimeout(() => controller.abort(), requestTimeoutMs) : null;
      try {
        const requestBody = {
          message: String(question).trim().slice(0, 4000),
          language: local.language,
          history: cleanHistory(history)
        };
        const requestContext = core && core.cleanRequestContext(coreContext);
        if (requestContext) requestBody.core_context = requestContext;
        const response = await fetchImpl(`${baseUrl}/v1/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody),
          signal: controller ? controller.signal : undefined,
          credentials: 'omit',
          referrerPolicy: 'no-referrer'
        });
        if (!response.ok) throw new Error('remote response was not successful');

        const payload = await response.json();
        if (!payload || typeof payload.reply !== 'string' || !['uk', 'ru'].includes(payload.language)) {
          throw new Error('remote response contract mismatch');
        }
        const citation = Array.isArray(payload.citations) ? payload.citations[0] : null;
        const source = citation && citation.url && citation.title
          ? { file: citation.title, url: citation.url, status: citation.status || 'PROPOSED' }
          : null;

        return {
          ...local,
          core: (core && core.cleanResponseContext(payload.core)) || coreContext,
          text: payload.reply,
          language: payload.language,
          source,
          transport: 'remote',
          provider: payload.provider || 'server',
          requestId: payload.request_id || null,
          validationState: payload.validation_state || 'PROPOSED'
        };
      } catch {
        return { ...localResult, transport: 'local-fallback', provider: 'local-knowledge' };
      } finally {
        if (timer) clearTimeout(timer);
      }
    }

    return Object.freeze({ reply, isRemoteEnabled });
  }

  const api = { create, safeBaseUrl, cleanHistory };
  if (typeof globalThis !== 'undefined') globalThis.ROZUMAssistantClient = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
