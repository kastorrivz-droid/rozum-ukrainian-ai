const assert = require('node:assert/strict');
const engine = require('../assets/assistant-engine.js');
const clientModule = require('../assets/assistant-client.js');

(async () => {
  assert.equal(clientModule.safeBaseUrl('http://example.com'), '');
  assert.equal(clientModule.safeBaseUrl('https://api.example.com/'), 'https://api.example.com');
  assert.equal(clientModule.safeBaseUrl('http://127.0.0.1:8000/'), 'http://127.0.0.1:8000');
  assert.equal(clientModule.safeBaseUrl('https://user:secret@api.example.com'), '');
  assert.equal(clientModule.safeBaseUrl('https://api.example.com?token=public-but-wrong'), '');
  console.log('PASS safe API URL policy');

  assert.deepEqual(clientModule.cleanCitation({
    title: '06_REEVES.md',
    url: 'https://github.com/kastorrivz-droid/rozum-ukrainian-ai/blob/main/06_REEVES.md',
    status: 'PROPOSED'
  }), {
    file: '06_REEVES.md',
    url: 'https://github.com/kastorrivz-droid/rozum-ukrainian-ai/blob/main/06_REEVES.md',
    status: 'PROPOSED'
  });
  assert.equal(clientModule.cleanCitation({
    title: '06_REEVES.md',
    url: 'javascript:alert(1)',
    status: 'PROPOSED'
  }), null);
  assert.equal(clientModule.cleanCitation({
    title: '06_REEVES.md',
    url: 'https://github.com/kastorrivz-droid/rozum-ukrainian-ai/blob/main/01_ROZUM_VISION.md',
    status: 'PROPOSED'
  }), null);
  console.log('PASS citations are restricted to the public ROZUM repository');

  assert.deepEqual(clientModule.cleanWebCitation({
    title: 'Cloudflare Web Search API',
    url: 'https://developers.cloudflare.com/web-search/#overview',
    status: 'anything supplied by the network'
  }), {
    file: 'Cloudflare Web Search API',
    title: 'Cloudflare Web Search API',
    url: 'https://developers.cloudflare.com/web-search/',
    status: 'EXTERNAL / UNVALIDATED',
    kind: 'web'
  });
  assert.equal(clientModule.cleanWebCitation({ title: 'Unsafe', url: 'javascript:alert(1)' }), null);
  assert.equal(clientModule.cleanWebCitation({ title: 'Credentials', url: 'https://user:secret@example.com/' }), null);
  console.log('PASS external web citations are sanitized and explicitly unvalidated');

  const localClient = clientModule.create({
    engine,
    config: { apiEnabled: false, apiBaseUrl: 'https://api.example.com' }
  });
  const local = await localClient.reply('Кто такой Ривз?', engine.createSession('ru'));
  assert.equal(local.transport, 'local');
  assert.equal(local.id, 'reeves');
  assert.equal(localClient.isRemoteEnabled, false);
  console.log('PASS disabled API stays local');

  let captured;
  const remoteClient = clientModule.create({
    engine,
    config: { apiEnabled: true, apiBaseUrl: 'https://api.example.com/', requestTimeoutMs: 5000 },
    fetchImpl: async (url, options) => {
      captured = { url, options };
      return {
        ok: true,
        async json() {
          return {
            request_id: 'request-1',
            reply: 'Серверный ответ Ривза.',
            language: 'ru',
            provider: 'mock',
            validation_state: 'PROPOSED',
            citations: [{
              title: '06_REEVES.md',
              url: 'https://github.com/kastorrivz-droid/rozum-ukrainian-ai/blob/main/06_REEVES.md',
              status: 'PROPOSED'
            }],
            web_citations: [{
              title: 'Current external source',
              url: 'https://example.com/current#section',
              status: 'EXTERNAL / UNVALIDATED'
            }],
            web_search: { requested: true, status: 'success', result_count: 1 }
          };
        }
      };
    }
  });
  const remote = await remoteClient.reply(
    'Кто такой Ривз?',
    engine.createSession('ru'),
    [{ role: 'user', content: 'Предыдущий вопрос' }],
    { webSearch: true }
  );
  assert.equal(captured.url, 'https://api.example.com/v1/chat');
  assert.equal(captured.options.credentials, 'omit');
  assert.equal(JSON.parse(captured.options.body).history.length, 1);
  assert.equal(JSON.parse(captured.options.body).web_search, true);
  assert.equal(remote.transport, 'remote');
  assert.equal(remote.text, 'Серверный ответ Ривза.');
  assert.equal(remote.source.file, '06_REEVES.md');
  assert.equal(remote.sources.length, 2);
  assert.equal(remote.sources[1].kind, 'web');
  assert.equal(remote.webSearchStatus, 'success');
  assert.equal(remote.provider, 'mock');
  console.log('PASS remote contract mapping');

  const fallbackClient = clientModule.create({
    engine,
    config: { apiEnabled: true, apiBaseUrl: 'https://api.example.com' },
    fetchImpl: async () => { throw new Error('offline'); }
  });
  const fallback = await fallbackClient.reply('Що таке ROZUM OS?', engine.createSession('uk'));
  assert.equal(fallback.transport, 'local-fallback');
  assert.equal(fallback.id, 'overview');
  console.log('PASS network failure falls back locally');

  const cleaned = clientModule.cleanHistory([
    { role: 'system', content: 'not allowed' },
    { role: 'user', content: '  valid  ' },
    null
  ]);
  assert.deepEqual(cleaned, [{ role: 'user', content: 'valid' }]);
  console.log('PASS history contract is bounded');
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
