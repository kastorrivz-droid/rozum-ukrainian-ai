(() => {
  'use strict';
  const ALLOWED_ROUTES = new Set(['project_knowledge', 'general_dialogue']);
  const TOPIC_ID = /^[a-z][a-z0-9_]{0,31}$/;
  function create(options = {}) {
    const engine = options.engine || globalThis.ROZUMAssistantEngine;
    const topicIds = new Set((engine && Array.isArray(engine.topics) ? engine.topics : [])
      .map(topic => topic && topic.id)
      .filter(id => typeof id === 'string' && TOPIC_ID.test(id)));
    function classify(result) {
      const responseId = result && typeof result.id === 'string' ? result.id : '';
      const stateTopic = result && result.state && typeof result.state.topic === 'string' ? result.state.topic : '';
      const topicId = topicIds.has(responseId)
        ? responseId
        : (responseId === 'fallback' && topicIds.has(stateTopic) ? stateTopic : null);
      const projectAnswer = Boolean(topicId || (result && result.source));
      return Object.freeze({ route: projectAnswer ? 'project_knowledge' : 'general_dialogue', topic_id: topicId });
    }
    function cleanRequestContext(value) {
      if (!value || typeof value !== 'object') return null;
      const route = ALLOWED_ROUTES.has(value.route) ? value.route : null;
      if (!route) return null;
      const topicId = typeof value.topic_id === 'string' && TOPIC_ID.test(value.topic_id) && topicIds.has(value.topic_id)
        ? value.topic_id
        : null;
      return { route, topic_id: topicId };
    }
    function cleanResponseContext(value) {
      const safe = cleanRequestContext(value);
      if (!safe) return null;
      const sources = Array.isArray(value.sources_used)
        ? value.sources_used.filter(name => typeof name === 'string' && /^[0-9]{2}_[A-Z0-9_]+\.md$/.test(name)).slice(0, 2)
        : [];
      return { ...safe, sources_used: sources };
    }
    return Object.freeze({ classify, cleanRequestContext, cleanResponseContext });
  }
  const api = { create };
  if (typeof globalThis !== 'undefined') globalThis.ROZUMAssistantCore = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
