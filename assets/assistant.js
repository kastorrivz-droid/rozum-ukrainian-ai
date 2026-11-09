(() => {
  'use strict';

  const engine = globalThis.ROZUMAssistantEngine;
  const clientFactory = globalThis.ROZUMAssistantClient;
  const memoryFactory = globalThis.ROZUMAssistantMemory;
  if (!engine || !clientFactory || !memoryFactory) return;
  const client = clientFactory.create({ engine });
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
      user: 'Ви', assistant: 'Ривз · публічна бета', searching: 'Шукаю відповідь у відкритій довідці', ready: 'Відповідь готова',
      cleared: 'Діалог очищено', session: turns => `Контекст сеансу · ${turns} ${turns === 1 ? 'відповідь' : 'відповідей'}`,
      source: 'Джерело', copy: 'Копіювати', copied: 'Скопійовано', placeholder: 'Запитайте про ROZUM…'
    },
    ru: {
      user: 'Вы', assistant: 'Ривз · публичная бета', searching: 'Ищу ответ в открытой справке', ready: 'Ответ готов',
      cleared: 'Диалог очищен', session: turns => `Контекст сеанса · ${turns} ${turns === 1 ? 'ответ' : 'ответов'}`,
      source: 'Источник', copy: 'Копировать', copied: 'Скопировано', placeholder: 'Спросите о ROZUM…'
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
    if (result.source) {
      const source = document.createElement('a');
      source.className = 'message-source';
      source.href = result.source.url;
      source.target = '_blank';
      source.rel = 'noopener noreferrer';
      source.textContent = `${ui[result.language].source}: ${result.source.file}`;
      const status = document.createElement('span');
      status.className = 'source-status';
      status.textContent = result.source.status;
      footer.append(source, status);
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

  function addTyping(language) {
    const typing = document.createElement('div');
    typing.className = 'message bot typing';
    typing.setAttribute('aria-label', ui[language].searching);
    typing.innerHTML = '<i></i><i></i><i></i>';
    messages.append(typing);
    scrollToLatest();
    return typing;
  }

  function setBusy(isBusy) {
    sendButton.disabled = isBusy;
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
    const typing = addTyping(language);
    liveStatus.textContent = ui[language].searching;

    const minimumDelay = new Promise(resolve => window.setTimeout(resolve, 250));
    const [result] = await Promise.all([
      client.reply(question, session, conversationHistory),
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
    assistantMode.lastChild.textContent = ' Публічна бета · захищений серверний діалог';
    privacyNote.innerHTML = '<strong>Важливо:</strong> серверний режим увімкнений: поточне повідомлення та до 12 останніх реплік надсилаються серверу й налаштованому постачальнику мовної моделі. Сервер не зберігає історію; локальна пам’ять працює лише після вашої згоди. Не вводьте особисті чи секретні дані.';
  }
})();
