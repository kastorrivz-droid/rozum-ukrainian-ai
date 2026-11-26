import assert from "node:assert/strict";
import { test } from "node:test";
import worker from "./src/index.js";

const origin = "https://kastorrivz-droid.github.io";

test("health route reports the configured model without requiring chat input", async () => {
  const response = await worker.fetch(new Request("https://worker.test/healthz"), { AI: {} });
  const body = await response.json();
  assert.equal(response.status, 200);
  assert.equal(body.status, "healthy");
  assert.equal(body.model, "@cf/google/gemma-4-26b-a4b-it");
  assert.equal(body.capabilities.web_search, "disabled");
  assert.equal(response.headers.get("X-Frame-Options"), "DENY");
  assert.match(response.headers.get("Content-Security-Policy"), /default-src 'none'/);
});

test("ready route fails closed when the model binding is unavailable", async () => {
  const unavailable = await worker.fetch(new Request("https://worker.test/readyz"), { AI: {} });
  assert.equal(unavailable.status, 503);
  assert.equal((await unavailable.json()).status, "not_ready");

  const ready = await worker.fetch(new Request("https://worker.test/readyz"), {
    AI: { run: async () => ({ response: "unused" }), websearch: async () => Response.json({ items: [] }) },
    WEB_SEARCH_ENABLED: "true"
  });
  const body = await ready.json();
  assert.equal(ready.status, 200);
  assert.equal(body.status, "ready");
  assert.equal(body.capabilities.chat, true);
  assert.equal(body.capabilities.web_search, "enabled");
});

test("short Russian greeting is not misclassified as Ukrainian", async () => {
  const response = await worker.fetch(new Request("https://worker.test/v1/chat", {
    method: "POST",
    headers: { Origin: origin, "Content-Type": "application/json" },
    body: JSON.stringify({
      message: "Ривз привет",
      language: "auto",
      core_context: { route: "general_dialogue", topic_id: null }
    })
  }), { AI: { run: async () => ({ response: "Привет! Я на связи." }) } });
  const body = await response.json();
  assert.equal(response.status, 200);
  assert.equal(body.language, "ru");
});

test("chat preserves the public browser API response contract", async () => {
  let observedModel = "";
  let observedMessages = [];
  const env = {
    AI: {
      run: async (model, input) => {
        observedModel = model;
        observedMessages = input.messages;
        return { response: "Вітаю! Це тестова відповідь українською." };
      }
    }
  };
  const response = await worker.fetch(new Request("https://worker.test/v1/chat", {
    method: "POST",
    headers: { Origin: origin, "Content-Type": "application/json" },
    body: JSON.stringify({ message: "Привіт, відповідай українською", language: "uk", history: [] })
  }), env);
  const body = await response.json();

  assert.equal(response.status, 200);
  assert.equal(observedModel, "@cf/google/gemma-4-26b-a4b-it");
  assert.equal(observedMessages[0].role, "system");
  assert.equal(body.reply, "Вітаю! Це тестова відповідь українською.");
  assert.equal(body.language, "uk");
  assert.equal(body.provider, "cloudflare-workers-ai");
  assert.equal(body.memory_persisted, false);
  assert.equal(response.headers.get("Access-Control-Allow-Origin"), origin);
});

test("chat uses bounded non-stored generation settings", async () => {
  let observedInput;
  const env = {
    AI: {
      run: async (_model, input) => {
        observedInput = input;
        return { response: "Коротка відповідь." };
      }
    }
  };
  const response = await worker.fetch(new Request("https://worker.test/v1/chat", {
    method: "POST",
    headers: { Origin: origin, "Content-Type": "application/json" },
    body: JSON.stringify({ message: "Привіт", language: "uk" })
  }), env);
  assert.equal(response.status, 200);
  assert.equal(observedInput.max_completion_tokens, 500);
  assert.deepEqual(observedInput.chat_template_kwargs, { enable_thinking: false });
  assert.equal(Object.hasOwn(observedInput, "max_tokens"), false);
  assert.equal(observedInput.store, false);
  assert.equal(observedInput.stream, false);
});

test("general questions use the model without invented ROZUM citations", async () => {
  const answers = new Map([
    ["Какая столица Франции?", "Столица Франции — Париж."],
    ["Сколько будет семь умножить на восемь?", "Семь умножить на восемь — 56."],
    ["Чому небо блакитне?", "Небо здається блакитним через розсіювання світла."]
  ]);
  const env = {
    AI: {
      run: async (_model, input) => {
        const message = input.messages[input.messages.length - 1].content;
        return { response: answers.get(message) };
      }
    }
  };
  for (const [message, expected] of answers) {
    const language = message.startsWith("Чому") ? "uk" : "ru";
    const response = await worker.fetch(new Request("https://worker.test/v1/chat", {
      method: "POST",
      headers: { Origin: origin, "Content-Type": "application/json" },
      body: JSON.stringify({ message, language: "auto" })
    }), env);
    const payload = await response.json();
    assert.equal(response.status, 200);
    assert.equal(payload.reply, expected);
    assert.equal(payload.language, language);
    assert.deepEqual(payload.citations, []);
    assert.equal(payload.core.route, "general_dialogue");
    assert.deepEqual(payload.core.sources_used, []);
  }
});

test("general dialogue does not inherit ROZUM citations from prior history", async () => {
  let observedMessages;
  const env = {
    AI: {
      run: async (_model, input) => {
        observedMessages = input.messages;
        return { response: "Спокойная короткая мантра без проектных утверждений." };
      }
    }
  };
  const response = await worker.fetch(new Request("https://worker.test/v1/chat", {
    method: "POST",
    headers: { Origin: origin, "Content-Type": "application/json" },
    body: JSON.stringify({
      message: "Сделай короткую мантру для спокойного сна.",
      language: "ru",
      history: [
        { role: "user", content: "Расскажи о ролях ROZUM и Ривзе" },
        { role: "assistant", content: "Ривз объясняет, Argos проверяет маршрут." }
      ],
      core_context: { route: "general_dialogue", topic_id: null }
    })
  }), env);
  const body = await response.json();
  assert.equal(response.status, 200);
  assert.deepEqual(body.citations, []);
  assert.deepEqual(body.core.sources_used, []);
  assert.doesNotMatch(observedMessages.at(-1).content, /Public ROZUM source excerpts/);
});

test("requested web search is grounded, sanitized, and returned as external citations", async () => {
  let observedSearch;
  let observedMessages;
  const env = {
    WEB_SEARCH_ENABLED: "true",
    AI: {
      websearch: async (input) => {
        observedSearch = input;
        return Response.json({
          items: [
            {
              title: "Cloudflare Web Search API",
              url: "https://developers.cloudflare.com/web-search/#overview",
              description: "Current documentation for grounded web search."
            },
            {
              title: "Unsafe result",
              url: "javascript:alert(1)",
              description: "This must not reach the model or browser."
            },
            {
              title: "Insecure result",
              url: "http://example.com/plaintext",
              description: "Plain HTTP must not reach the model or browser."
            }
          ]
        });
      },
      run: async (_model, input) => {
        observedMessages = input.messages;
        return { response: "Cloudflare має Web Search API [1]." };
      }
    }
  };
  const response = await worker.fetch(new Request("https://worker.test/v1/chat", {
    method: "POST",
    headers: { Origin: origin, "Content-Type": "application/json", "CF-Connecting-IP": "198.51.100.25" },
    body: JSON.stringify({ message: "Що нового у Cloudflare Web Search?", language: "uk", web_search: true })
  }), env);
  const body = await response.json();

  assert.equal(response.status, 200);
  assert.deepEqual(observedSearch, {
    gatewayId: "default",
    query: "Що нового у Cloudflare Web Search?",
    provider: "ceramic",
    limit: 5
  });
  assert.match(observedMessages[0].content, /external sources, not validated ROZUM facts/i);
  assert.match(observedMessages.at(-1).content, /Cloudflare Web Search API/);
  assert.doesNotMatch(observedMessages.at(-1).content, /javascript:alert/);
  assert.doesNotMatch(observedMessages.at(-1).content, /example.com\/plaintext/);
  assert.equal(body.web_search.status, "success");
  assert.equal(body.web_search.result_count, 1);
  assert.equal(body.web_citations.length, 1);
  assert.equal(body.web_citations[0].status, "EXTERNAL / UNVALIDATED");
});

test("search provider failure does not fabricate live results", async () => {
  let observedSystem = "";
  const env = {
    WEB_SEARCH_ENABLED: "true",
    AI: {
      websearch: async () => new Response("credits required", { status: 402 }),
      run: async (_model, input) => {
        observedSystem = input.messages[0].content;
        return { response: "Живий пошук зараз недоступний." };
      }
    }
  };
  const response = await worker.fetch(new Request("https://worker.test/v1/chat", {
    method: "POST",
    headers: { Origin: origin, "Content-Type": "application/json", "CF-Connecting-IP": "198.51.100.26" },
    body: JSON.stringify({ message: "Які новини сьогодні?", language: "uk", web_search: true })
  }), env);
  const body = await response.json();

  assert.equal(response.status, 200);
  assert.equal(body.web_search.status, "unavailable");
  assert.deepEqual(body.web_citations, []);
  assert.match(observedSystem, /do not pretend current information was verified/i);
});

test("disabled web search fails closed without calling a provider", async () => {
  let searchCalled = false;
  const env = {
    WEB_SEARCH_ENABLED: "false",
    AI: {
      websearch: async () => {
        searchCalled = true;
        return Response.json({ items: [] });
      },
      run: async () => ({ response: "Веб-поиск временно отключён." })
    }
  };
  const response = await worker.fetch(new Request("https://worker.test/v1/chat", {
    method: "POST",
    headers: { Origin: origin, "Content-Type": "application/json" },
    body: JSON.stringify({ message: "Какие новости сегодня?", language: "ru", web_search: true })
  }), env);
  const body = await response.json();
  assert.equal(response.status, 200);
  assert.equal(searchCalled, false);
  assert.equal(body.web_search.status, "disabled");
  assert.equal(body.web_search.provider, null);
});

test("chat rejects origins outside the allowlist", async () => {
  const response = await worker.fetch(new Request("https://worker.test/v1/chat", {
    method: "POST",
    headers: { Origin: "https://example.com", "Content-Type": "application/json" },
    body: JSON.stringify({ message: "hello" })
  }), { AI: {} });
  assert.equal(response.status, 403);
});

test("chat rejects malformed JSON", async () => {
  const response = await worker.fetch(new Request("https://worker.test/v1/chat", {
    method: "POST",
    headers: { Origin: origin, "Content-Type": "application/json" },
    body: "{broken"
  }), { AI: {} });
  assert.equal(response.status, 400);
});

test("chat requires the exact JSON media type", async () => {
  const response = await worker.fetch(new Request("https://worker.test/v1/chat", {
    method: "POST",
    headers: { Origin: origin, "Content-Type": "application/jsonp" },
    body: JSON.stringify({ message: "hello" })
  }), { AI: {} });
  assert.equal(response.status, 415);
});

test("chat rejects overlong messages instead of silently truncating them", async () => {
  const response = await worker.fetch(new Request("https://worker.test/v1/chat", {
    method: "POST",
    headers: { Origin: origin, "Content-Type": "application/json" },
    body: JSON.stringify({ message: "x".repeat(4001) })
  }), { AI: { run: async () => ({ response: "unused" }) } });
  const body = await response.json();
  assert.equal(response.status, 422);
  assert.equal(body.error.code, "MESSAGE_TOO_LONG");
});
