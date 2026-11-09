const assert = require('node:assert/strict');
const engine = require('../assets/assistant-engine.js');
const clientModule = require('../assets/assistant-client.js');

(async () => {
  assert.equal(clientModule.safeBaseUrl('http://example.com'), '');
  assert.equal(clientModule.safeBaseUrl('https://api.example.com/'), 'https://api.example.com');
  assert.equal(clientModule.safeBaseUrl('http://127.0.0.1:8000/'), 'http://127.0.0.1:8000');
  console.log('PASS safe API URL policy');

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
            citations: [{ title: '06_REEVES.md', url: 'https://example.com/reeves', status: 'PROPOSED' }]
          };
        }
      };
    }
  });
  const remote = await remoteClient.reply(
    'Кто такой Ривз?',
    engine.createSession('ru'),
    [{ role: 'user', content: 'Предыдущий вопрос' }]
  );
  assert.equal(captured.url, 'https://api.example.com/v1/chat');
  assert.equal(captured.options.credentials, 'omit');
  assert.equal(JSON.parse(captured.options.body).history.length, 1);
  assert.equal(remote.transport, 'remote');
  assert.equal(remote.text, 'Серверный ответ Ривза.');
  assert.equal(remote.source.file, '06_REEVES.md');
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
