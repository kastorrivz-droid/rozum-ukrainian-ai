const assert = require('node:assert/strict');
const memoryModule = require('../assets/assistant-memory.js');

function fakeStorage() {
  const values = new Map();
  return {
    getItem: key => values.has(key) ? values.get(key) : null,
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: key => values.delete(key)
  };
}

const storage = fakeStorage();
const memory = memoryModule.create({ storage });
assert.equal(memory.isEnabled(), false);
assert.deepEqual(memory.append({ role: 'user', content: 'not stored' }), []);
assert.deepEqual(memory.load(), []);
console.log('PASS memory is opt-in');

assert.equal(memory.setConsent(true), true);
memory.append([
  { role: 'user', content: '  Привіт  ' },
  { role: 'assistant', content: 'Вітаю!' },
  { role: 'system', content: 'not allowed' }
]);
assert.equal(memory.load().length, 2);
assert.equal(memory.load()[0].content, 'Привіт');
console.log('PASS consented history is sanitized');

for (let index = 0; index < 50; index += 1) {
  memory.append({ role: 'user', content: `turn-${index}` });
}
assert.equal(memory.load().length, memory.maxTurns);
assert.equal(memory.load().at(-1).content, 'turn-49');
console.log('PASS history is bounded');

memory.clear();
assert.deepEqual(memory.load(), []);
memory.append({ role: 'user', content: 'new' });
assert.equal(memory.setConsent(false), false);
assert.deepEqual(memory.load(), []);
console.log('PASS revoking consent deletes history');
