const assert = require('node:assert/strict');
const engine = require('../assets/assistant.js');

const cases = [
  ['Що таке ROZUM OS?', 'overview', 'uk'],
  ['Кто такой Ривз?', 'reeves', 'ru'],
  ['Що робить Argos?', 'argos', 'uk'],
  ['Как проверяются факты?', 'verification', 'ru'],
  ['Что умеет это демо?', 'demo', 'ru'],
  ['Как работает ROZUM?', 'overview', 'ru'],
  ['Який статус проєкту?', 'status', 'uk'],
  ['Как присоединиться?', 'participate', 'ru'],
  ['невідоме запитання', 'fallback', 'uk']
];

for (const [question, expectedId, expectedLanguage] of cases) {
  const result = engine.reply(question);
  assert.equal(result.id, expectedId, question);
  assert.equal(result.language, expectedLanguage, question);
  assert.ok(result.text.length > 40, question);
  console.log(`PASS ${expectedId}: ${result.id}/${result.language}`);
}
