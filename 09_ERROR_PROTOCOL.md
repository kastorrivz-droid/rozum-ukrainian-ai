# 09 — Error Protocol

**Status:** VALIDATED

## Формат ошибки

```json
{
  "protocol": "ROZUM_AI_v2",
  "protocol_version": "2.1",
  "id": "NEW-UUID-V4",
  "timestamp": "2026-09-02T00:00:00Z",
  "sender_id": "receiver_id",
  "key_id": "receiver-key-v1",
  "author": {"id": "receiver_id", "role": "system"},
  "intent": "protocol_error",
  "reply_to": "INCOMING-MESSAGE-ID",
  "context": {"session_id": "ORIGINAL-SESSION", "state": {"accepted": false}},
  "data": {
    "error": {
      "code": "SIGNATURE_VERIFICATION_FAILED",
      "stage": 4,
      "retryable": false,
      "message": "Cryptographic verification failed",
      "details": {}
    }
  },
  "question": "",
  "output_format": "protocol",
  "signature": null
}
```

Если входной пакет разрушен настолько, что `id` или `session_id` нельзя безопасно прочитать, поля связи могут быть `null` только во внешнем транспортном ответе, а не в конверте, который заявлен как валидный ROZUM_AI_v2.1.

## Коды

| Код | Stage | Retry | Значение |
|---|---:|---:|---|
| `SCHEMA_INVALID` | 1 | false | Нарушена JSON Schema |
| `UNSUPPORTED_PROTOCOL_VERSION` | 1 | false | Версия не поддерживается |
| `SEMANTIC_INVALID` | 2 | depends | Нарушено семантическое правило |
| `TIMESTAMP_OUT_OF_WINDOW` | 2 | true | Время вне допустимого окна |
| `SENDER_KEY_MISMATCH` | 2 | false | `sender_id` не связан с `key_id` |
| `REPLAY_SUSPECTED` | 3 | false | Быстрый слой обнаружил вероятный повтор |
| `SIGNATURE_REQUIRED` | 4 | false | Политика требует подпись, получен `null` |
| `KEY_NOT_FOUND` | 4 | false | Ключ не найден |
| `SIGNATURE_FORMAT_INVALID` | 4 | false | Base64/длина/профиль неверны |
| `SIGNATURE_VERIFICATION_FAILED` | 4 | false | Математическая проверка не пройдена |
| `REPLAY_CONFLICT` | 5 | false | `id` уже атомарно зафиксирован |
| `INTENT_NOT_SUPPORTED` | app | false | Получатель не поддерживает `intent` |
| `INTERNAL_ERROR` | app | true | Контролируемая внутренняя ошибка |

## Правила

- не возвращать секреты, приватные ключи или исходный MAC;
- не маскировать ошибку подписи как обычный бизнес-отказ;
- сохранять `reply_to` и `session_id`, когда они уже безопасно извлечены;
- `retryable: true` не разрешает повторно использовать тот же `id`: повторная попытка получает новый UUIDv4.

