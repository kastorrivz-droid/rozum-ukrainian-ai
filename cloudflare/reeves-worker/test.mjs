import assert from "node:assert/strict";
import { test } from "node:test";
import worker from "./src/index.js";

const origin = "https://kastorrivz-droid.github.io";

test("health route reports the configured model without requiring chat input", async () => {
  const response = await worker.fetch(new Request("https://worker.test/healthz"), { AI: {} });
  const body = await response.json();
  assert.equal(response.status, 200);
  assert.equal(body.model, "@cf/google/gemma-4-26b-a4b-it");
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
