const assert = require('node:assert/strict');
const engine = require('../assets/assistant-engine.js');
const coreFactory = require('../assets/assistant-core.js');

function ask(text, session = engine.createSession()) {
  const result = engine.reply(text, session);
  assert.ok(result.text.length > 30, text);
  assert.ok(Array.isArray(result.suggestions), text);
  assert.ok(result.state.turns === session.turns + 1, text);
  return result;
}

const standaloneCases = [
  ['Що таке ROZUM OS?', 'overview', 'uk'],
  ['Кто такой Ривз?', 'reeves', 'ru'],
  ['Що робить Argos?', 'argos', 'uk'],
  ['Как проверяются факты?', 'verification', 'ru'],
  ['Что умеет эта бета?', 'demo', 'ru'],
  ['Как работает ROZUM?', 'overview', 'ru'],
  ['Який статус проєкту?', 'status', 'uk'],
  ['Как присоединиться?', 'participate', 'ru'],
  ['Что означает VALIDATED?', 'lifecycle', 'ru'],
  ['Как устроена безопасность?', 'security', 'ru'],
  ['Какие принципы ROZUM?', 'principles', 'ru'],
  ['Какие бывают ошибки протокола?', 'errors', 'ru'],
  ['Что проверено тестами?', 'tests', 'ru']
];

for (const [question, expectedId, expectedLanguage] of standaloneCases) {
  const result = ask(question);
  assert.equal(result.id, expectedId, question);
  assert.equal(result.language, expectedLanguage, question);
  console.log(`PASS ${expectedId}: ${result.id}/${result.language}`);
}

assert.equal(engine.detectLanguage('Какая столица Франции?'), 'ru');
assert.equal(engine.detectLanguage('Яка столиця Франції?'), 'uk');
assert.equal(engine.detectLanguage('Ривз привет'), 'ru');
assert.equal(engine.detectLanguage('Рівз привіт'), 'uk');
console.log('PASS general-question language detection');

let conversation = engine.createSession('ru');
const first = ask('Расскажи про Ривза', conversation);
conversation = first.state;
const more = ask('подробнее', conversation);
assert.equal(more.id, 'reeves');
assert.equal(more.mode, 'detail');
conversation = more.state;
const example = ask('приведи пример', conversation);
assert.equal(example.id, 'reeves');
assert.equal(example.mode, 'example');
console.log('PASS multi-turn topic context');

const comparison = ask('Чем Ривз отличается от Argos?', example.state);
assert.equal(comparison.id, 'comparison');
assert.equal(comparison.mode, 'comparison');
assert.match(comparison.text, /Ривз|Reeves/);
assert.match(comparison.text, /Argos/);
console.log('PASS role comparison');

const roles = ask('Расскажи о ролях ROZUM и Ривзе', engine.createSession('ru'));
const mantra = ask('Сделай короткую мантру для спокойного сна.', roles.state);
assert.equal(mantra.id, 'fallback');
assert.equal(mantra.source, null);
assert.deepEqual(coreFactory.create({ engine }).classify(mantra), {
  route: 'general_dialogue',
  topic_id: null
});
const projectWellbeing = ask('Как ROZUM учитывает усталость человека?', engine.createSession('ru'));
assert.equal(projectWellbeing.id, 'wellbeing');
console.log('PASS general wellbeing request does not inherit project citations');

const sourceTopic = ask('Что такое протокол?', engine.createSession('ru'));
const source = ask('Какой источник?', sourceTopic.state);
assert.equal(source.id, 'source');
assert.match(source.text, /02_ROZUM_AI_v2_SPEC\.md/);
console.log('PASS source follow-up');

const fallback = ask('невідоме запитання', engine.createSession('uk'));
assert.equal(fallback.id, 'fallback');
assert.equal(fallback.language, 'uk');

const privateInput = 'Меня зовут Алексей';
const introduction = ask(privateInput, engine.createSession('ru'));
assert.equal(introduction.id, 'introduction');
assert.ok(!JSON.stringify(introduction.state).includes('Алексей'));
console.log('PASS session does not retain user text');

assert.ok(engine.topics.length >= 21);
assert.equal(engine.topics.find(topic => topic.id === 'argos').source.status, 'VALIDATED');
assert.equal(engine.topics.find(topic => topic.id === 'reeves').source.status, 'PROPOSED');
console.log(`PASS knowledge base: ${engine.topics.length} topics`);

for (const topic of engine.topics) {
  const suggestedUk = ask(`Розкажи про ${topic.label.uk}`, engine.createSession('uk'));
  const suggestedRu = ask(`Расскажи про ${topic.label.ru}`, engine.createSession('ru'));
  assert.equal(suggestedUk.id, topic.id, `UA suggestion route: ${topic.id}`);
  assert.equal(suggestedRu.id, topic.id, `RU suggestion route: ${topic.id}`);
}
console.log('PASS every dynamic topic suggestion in UA/RU');
