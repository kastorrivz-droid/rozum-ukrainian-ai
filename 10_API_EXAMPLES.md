# 10 — API Examples

**Status:** DRAFT / NON-NORMATIVE EXAMPLES

Примеры показывают форму обмена. При расхождении приоритет имеют `02`, `03` и `08`.

## 1. Ручной неподписанный запрос к Andromeda

```json
{
  "protocol": "ROZUM_AI_v2",
  "protocol_version": "2.1",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-08-31T10:40:00Z",
  "sender_id": "human_vladislav",
  "key_id": "manual-channel",
  "author": {"id": "Vladislav", "role": "architect"},
  "intent": "system_architecture_analyze",
  "reply_to": null,
  "context": {"session_id": "sess_2026_08", "state": {"phase": 2}},
  "data": {"target": "ROZUM_AI_v2", "focus": ["schema", "interoperability"]},
  "question": "Проверь архитектуру и предложи следующий воспроизводимый тест",
  "output_format": "protocol",
  "signature": null
}
```

## 2. Ответ с сохранением связи

```json
{
  "protocol": "ROZUM_AI_v2",
  "protocol_version": "2.1",
  "id": "7f0d9b8a-2f43-4d51-9e6a-8a3a9c7e1b21",
  "timestamp": "2026-08-31T10:41:00Z",
  "sender_id": "superhuman_go_andromeda",
  "key_id": "manual-channel",
  "author": {"id": "Andromeda", "role": "navigator"},
  "intent": "inter_ai_task_response",
  "reply_to": "550e8400-e29b-41d4-a716-446655440000",
  "context": {"session_id": "sess_2026_08", "state": {"phase": 2, "status": "processed"}},
  "data": {"result": "accepted_for_review", "next_test": "CVT-001"},
  "question": "",
  "output_format": "protocol",
  "signature": null
}
```

## 3. Запрос Argos на мониторинг

```json
{
  "protocol": "ROZUM_AI_v2",
  "protocol_version": "2.1",
  "id": "6ba7b810-9dad-41d1-80b4-00c04fd430c8",
  "timestamp": "2026-09-02T20:00:00Z",
  "sender_id": "reeves_interface",
  "key_id": "key-v1",
  "author": {"id": "human_vladislav", "role": "architect"},
  "intent": "argos_monitor",
  "reply_to": null,
  "context": {"session_id": "sess_2026_09", "state": {"mode": "validate"}},
  "data": {
    "subject": "protocol_conformance",
    "success_criteria": ["schema_pass", "signature_pass", "replay_commit_pass"]
  },
  "question": "Зафиксировать результат проверки",
  "output_format": "protocol",
  "signature": null
}
```

## 4. Правило для примеров

UUID, время и подписи в документации не превращаются в реальные доказательства. Реальная подпись должна вычисляться из реальных канонических байтов; иначе ставится `null`.

