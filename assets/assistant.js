(() => {
  'use strict';

  const engine = globalThis.ROZUMAssistantEngine;
  const clientFactory = globalThis.ROZUMAssistantClient;
  const memoryFactory = globalThis.ROZUMAssistantMemory;
  const coreFactory = globalThis.ROZUMAssistantCore;
  if (!engine || !clientFactory || !memoryFactory || !coreFactory) return;
  const client = clientFactory.create({ engine, core: coreFactory });
  const memory = memoryFactory.create();

  const messages = document.getElementById('messages');
  const form = document.getElementById('chat');
  const input = document.getElementById('message');
  const counter = document.getElementById('counter');
  const clearButton = document.getElementById('clear-chat');
  const liveStatus = document.getElementById('live-status');
  const sessionState = document.getElementById('session-state');
  const chipsBox = document.getElementById('chips');
  const assistantMode = document.getElementById('assistant-mode');
  const privacyNote = document.getElementById('privacy-note');
  const webSearch = document.getElementById('web-search');
  const memoryConsent = document.getElementById('memory-consent');
  const memoryView = document.getElementById('memory-view');
  const memoryCount = document.getElementById('memory-count');
  const memoryDialog = document.getElementById('memory-dialog');
  const memoryList = document.getElementById('memory-list');
  const memoryClose = document.getElementById('memory-close');
  const memoryDelete = document.getElementById('memory-delete');
  const sendButton = form.querySelector('[type="submit"]');
  const initialMessage = messages.innerHTML;
  const initialChips = chipsBox.innerHTML;
  let session = engine.createSession('uk');
  let conversationHistory = memory.load().slice(-12).map(({ role, content }) => ({ role, content }));
  let requestToken = 0;
  let isPending = false;

  const ui = {
    uk: {
      user: 'Ви', assistant: 'Ривз · публічна бета', searching: 'Готую контекст ROZUM Core', webSearching: 'Шукаю актуальні джерела в інтернеті', ready: 'Відповідь готова',
      cleared: 'Діалог очищено', session: turns => `Контекст сеансу · ${turns} ${turns === 1 ? 'відповідь' : 'відповідей'}`,
      source: 'Джерело', webSource: 'Мережа', searchUnavailable: 'Веб-пошук недоступний', searchLimited: 'Ліміт веб-пошуку', copy: 'Копіювати', copied: 'Скопійовано', placeholder: 'Поставте запитання…'
    },
    ru: {
      user: 'Вы', assistant: 'Ривз · публичная бета', searching: 'Готовлю контекст ROZUM Core', webSearching: 'Ищу актуальные источники в интернете', ready: 'Ответ готов',
      cleared: 'Диалог очищен', session: turns => `Контекст сеанса · ${turns} ${turns === 1 ? 'ответ' : 'ответов'}`,
      source: 'Источник', webSource: 'Сеть', searchUnavailable: 'Веб-поиск недоступен', searchLimited: 'Лимит веб-поиска', copy: 'Копировать', copied: 'Скопировано', placeholder: 'Задайте вопрос…'
    }
  };

  function scrollToLatest() {
    messages.scrollTop = messages.scrollHeight;
  }

  function addUserMessage(text, language) {
    const article = document.createElement('article');
    article.className = 'message user';
    const role = document.createElement('span');
    role.className = 'message-role';
    role.textContent = ui[language].user;
    const body = document.createElement('p');
    body.textContent = text;
    article.append(role, body);
    messages.append(article);
    scrollToLatest();
  }

  function addBotMessage(result) {
    const article = document.createElement('article');
    article.className = 'message bot';
    const role = document.createElement('span');
    role.className = 'message-role';
    role.textContent = ui[result.language].assistant;
    const body = document.createElement('p');
    body.textContent = result.text;
    article.append(role, body);

    const footer = document.createElement('div');
    footer.className = 'message-footer';
    const resultSources = Array.isArray(result.sources)
      ? result.sources
      : (result.source ? [result.source] : []);
    if (resultSources.length) {
      const sourceList = document.createElement('div');
      sourceList.className = 'message-sources';
      resultSources.forEach(item => {
        const row = document.createElement('div');
        row.className = 'message-source-row';
        const source = document.createElement('a');
        source.className = 'message-source';
        source.href = item.url;
        source.target = '_blank';
        source.rel = 'noopener noreferrer';
        const label = item.kind === 'web' ? ui[result.language].webSource : ui[result.language].source;
        source.textContent = `${label}: ${item.file || item.title}`;
        const status = document.createElement('span');
        status.className = `source-status${item.kind === 'web' ? ' external' : ''}`;
        status.textContent = item.status;
        row.append(source, status);
        sourceList.append(row);
      });
      footer.append(sourceList);
    }
    if (['unavailable', 'empty', 'rate_limited'].includes(result.webSearchStatus)) {
      const searchState = document.createElement('span');
      searchState.className = 'search-state';
      searchState.textContent = result.webSearchStatus === 'rate_limited'
        ? ui[result.language].searchLimited
        : ui[result.language].searchUnavailable;
      footer.append(searchState);
    }

    const copy = document.createElement('button');
    copy.className = 'copy-button';
    copy.type = 'button';
    copy.textContent = ui[result.language].copy;
    copy.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(result.text);
        copy.textContent = ui[result.language].copied;
        window.setTimeout(() => { copy.textContent = ui[result.language].copy; }, 1200);
      } catch {
        copy.remove();
      }
    });
    footer.append(copy);
    article.append(footer);
    messages.append(article);
    scrollToLatest();
  }

  function addTyping(language, isWebSearch) {
    const typing = document.createElement('div');
    typing.className = 'message bot typing';
    typing.setAttribute('aria-label', isWebSearch ? ui[language].webSearching : ui[language].searching);
    typing.innerHTML = '<i></i><i></i><i></i>';
    messages.append(typing);
    scrollToLatest();
    return typing;
  }

  function setBusy(isBusy) {
    sendButton.disabled = isBusy;
    webSearch.disabled = isBusy;
    [...chipsBox.querySelectorAll('button')].forEach(chip => { chip.disabled = isBusy; });
    messages.setAttribute('aria-busy', String(isBusy));
  }

  function resizeInput() {
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, 132)}px`;
    counter.textContent = `${input.value.length}/600`;
  }

  function renderSuggestions(suggestions) {
    chipsBox.replaceChildren();
    suggestions.forEach(suggestion => {
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.q = suggestion.query;
      button.textContent = suggestion.label;
      button.addEventListener('click', () => send(suggestion.query));
      chipsBox.append(button);
    });
  }

  function updateSessionUI(language) {
    sessionState.textContent = ui[language].session(session.turns);
    input.placeholder = ui[language].placeholder;
  }

  function updateMemoryUI() {
    const enabled = memory.isEnabled();
    const saved = memory.load();
    memoryConsent.checked = enabled;
    memoryCount.textContent = String(saved.length);
    memoryView.disabled = !enabled;
  }

  function renderMemory() {
    const saved = memory.load();
    memoryList.replaceChildren();
    if (!saved.length) {
      const empty = document.createElement('p');
      empty.className = 'memory-empty';
      empty.textContent = 'Історія порожня.';
      memoryList.append(empty);
      return;
    }
    saved.forEach(turn => {
      const item = document.createElement('article');
      item.className = `memory-item ${turn.role}`;
      const role = document.createElement('strong');
      role.textContent = turn.role === 'user' ? 'Ви' : 'Ривз';
      const body = document.createElement('p');
      body.textContent = turn.content;
      const time = document.createElement('time');
      time.dateTime = turn.at;
      time.textContent = new Date(turn.at).toLocaleString();
      item.append(role, body, time);
      memoryList.append(item);
    });
  }

  async function send(value) {
    const question = String(value || '').trim();
    if (!question || isPending) return;

    const language = engine.detectLanguage(question, session.language);
    addUserMessage(question, language);
    input.value = '';
    resizeInput();
    setBusy(true);
    isPending = true;
    const token = ++requestToken;
    const useWebSearch = webSearch.checked;
    const typing = addTyping(language, useWebSearch);
    liveStatus.textContent = useWebSearch ? ui[language].webSearching : ui[language].searching;

    const minimumDelay = new Promise(resolve => window.setTimeout(resolve, 250));
    const [result] = await Promise.all([
      client.reply(question, session, conversationHistory, { webSearch: useWebSearch }),
      minimumDelay
    ]);
    if (token !== requestToken) return;

    try {
      typing.remove();
      session = result.state;
      conversationHistory.push(
        { role: 'user', content: question },
        { role: 'assistant', content: result.text }
      );
      conversationHistory = conversationHistory.slice(-12);
      memory.append([
        { role: 'user', content: question },
        { role: 'assistant', content: result.text }
      ]);
      updateMemoryUI();
      addBotMessage(result);
      renderSuggestions(result.suggestions);
      updateSessionUI(result.language);
      liveStatus.textContent = ui[result.language].ready;
      input.focus();
    } finally {
      isPending = false;
      setBusy(false);
    }
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    send(input.value);
  });

  input.addEventListener('input', resizeInput);
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  chipsBox.querySelectorAll('[data-q]').forEach(chip => chip.addEventListener('click', () => send(chip.dataset.q)));

  clearButton.addEventListener('click', () => {
    requestToken += 1;
    isPending = false;
    session = engine.createSession('uk');
    conversationHistory = [];
    messages.innerHTML = initialMessage;
    chipsBox.innerHTML = initialChips;
    chipsBox.querySelectorAll('[data-q]').forEach(chip => chip.addEventListener('click', () => send(chip.dataset.q)));
    setBusy(false);
    liveStatus.textContent = ui.uk.cleared;
    input.value = '';
    resizeInput();
    updateSessionUI('uk');
    input.focus();
  });

  memoryConsent.addEventListener('change', () => {
    const enabled = memory.setConsent(memoryConsent.checked);
    if (!enabled) conversationHistory = [];
    updateMemoryUI();
  });

  memoryView.addEventListener('click', () => {
    renderMemory();
    if (typeof memoryDialog.showModal === 'function') memoryDialog.showModal();
    else memoryDialog.setAttribute('open', '');
  });

  memoryClose.addEventListener('click', () => {
    if (typeof memoryDialog.close === 'function') memoryDialog.close();
    else memoryDialog.removeAttribute('open');
  });
  memoryDelete.addEventListener('click', () => {
    memory.clear();
    conversationHistory = [];
    renderMemory();
    updateMemoryUI();
  });

  resizeInput();
  updateSessionUI('uk');
  updateMemoryUI();
  if (client.isRemoteEnabled) {
    assistantMode.lastChild.textContent = ' Публічна бета · серверний AI-діалог';
    privacyNote.innerHTML = '<strong>Важливо:</strong> серверний режим увімкнений: поточне повідомлення, до 12 реплік контексту та коротка підказка ROZUM Core надсилаються серверу. Якщо ви вмикаєте веб-пошук, текст запитання також обробляє зовнішній пошуковий провайдер, а знайдені фрагменти передаються моделі як неперевірені джерела. Сервіс не зберігає історію діалогу; локальна пам’ять працює лише після вашої згоди. Не вводьте особисті чи секретні дані.';
  }
})();
