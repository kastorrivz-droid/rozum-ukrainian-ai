(() => {
  'use strict';

  const SOURCE_PATH_PREFIX = '/kastorrivz-droid/rozum-ukrainian-ai/blob/main/';
  const SOURCE_STATUSES = new Set([
    'PROPOSED',
    'VALIDATED',
    'ACCEPTED',
    'ACCEPTED / CONTROL DOCUMENT',
    'ACCEPTED / WORKING BASELINE',
    'VALIDATED / STRUCTURAL BASELINE',
    'NORMATIVE / LOCKED',
    'NORMATIVE / ACCEPTED',
    'INTERNAL / CONCEPT / NON-NORMATIVE'
  ]);

  function safeBaseUrl(value) {
    const raw = String(value || '').trim().replace(/\/+$/, '');
    if (!raw) return '';
    try {
      const parsed = new URL(raw);
      const local = parsed.hostname === '127.0.0.1' || parsed.hostname === 'localhost';
      const safeProtocol = parsed.protocol === 'https:' || (parsed.protocol === 'http:' && local);
      if (!safeProtocol || parsed.username || parsed.password || parsed.search || parsed.hash) return '';
      return `${parsed.origin}${parsed.pathname.replace(/\/+$/, '')}`;
    } catch {
      return '';
    }
  }

  function cleanCitation(value) {
    if (!value || typeof value !== 'object') return null;
    const title = String(value.title || '').trim();
    const status = String(value.status || '').trim();
    if (!/^[0-9]{2}_[A-Z0-9_]+\.md$/.test(title) || !SOURCE_STATUSES.has(status)) return null;
    try {
      const url = new URL(String(value.url || '').trim());
      const safeRepositoryPath = url.origin === 'https://github.com'
        && url.pathname === `${SOURCE_PATH_PREFIX}${title}`;
      if (!safeRepositoryPath || url.username || url.password || url.search || url.hash) return null;
      return { file: title, url: url.href, status };
    } catch {
      return null;
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
        const replyText = payload.reply.trim();
        if (!replyText || replyText.length > 8000) throw new Error('remote reply is outside the allowed bounds');
        const source = Array.isArray(payload.citations)
          ? payload.citations.slice(0, 2).map(cleanCitation).find(Boolean) || null
          : null;
        const provider = typeof payload.provider === 'string' && /^[a-z0-9-]{1,64}$/.test(payload.provider)
          ? payload.provider
          : 'server';

        return {
          ...local,
          core: (core && core.cleanResponseContext(payload.core)) || coreContext,
          text: replyText,
          language: payload.language,
          source,
          transport: 'remote',
          provider,
          requestId: typeof payload.request_id === 'string' ? payload.request_id.slice(0, 128) : null,
          validationState: 'PROPOSED'
        };
      } catch {
        return { ...localResult, transport: 'local-fallback', provider: 'local-knowledge' };
      } finally {
        if (timer) clearTimeout(timer);
      }
    }

    return Object.freeze({ reply, isRemoteEnabled });
  }

  const api = { create, safeBaseUrl, cleanCitation, cleanHistory };
  if (typeof globalThis !== 'undefined') globalThis.ROZUMAssistantClient = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
