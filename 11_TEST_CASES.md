# 11 — Test Cases

**Status:** VALIDATED

## Матрица

| ID | Уровень | Ожидание |
|---|---|---|
| `S-001` | Schema | Валидный конверт 2.1 проходит |
| `S-002` | Schema | Отсутствующее обязательное поле отклоняется |
| `S-003` | Schema | Не-UUIDv4 `id` отклоняется |
| `M-001` | Semantic | Timestamp UTC/Z в окне проходит |
| `M-002` | Semantic | Неизвестная версия отклоняется |
| `I-001` | Interop | Ответ сохраняет `session_id` |
| `I-002` | Interop | Ответ устанавливает `reply_to` на входной `id` |
| `C-001` | Crypto | RFC 8785 JCS даёт одинаковые байты |
| `C-002` | Crypto | Ed25519 RAW-64 проходит |
| `C-003` | Crypto | DER/non-64 signature отклоняется |
| `C-004` | Crypto | Изменение `data` ломает проверку |
| `R-001` | Replay | Первый atomic commit проходит |
| `R-002` | Replay | Второй commit того же `id` отклоняется |

## CVT-001 — зафиксированный результат

Путь: `tests/interoperability/CVT-001/`

`result.json` подтверждает:

1. JCS byte identity — `PASS`.
2. Детерминированная Ed25519-подпись — `PASS`.
3. Приём RAW-64 подписи — `PASS`.
4. Отказ DER/non-64 подписи — `PASS`.
5. Atomic replay commit — `PASS`.
6. Обнаружение изменения payload — `PASS`.

Общий статус: `PASS`.

### Контрольные значения

- SHA-256 канонической строки: `cc10de758f26c00f2a693a3e1dfefed43cb8ba44f2ee2a7e29930127b1a90db5`.
- Ed25519 signature Base64: `N8SXVRHHrj3RndcFkAx8WsqTH39DqdPCJVLqSvy9raB3zOszADIN+jqubVNZE5P5FomhdzW9/OCoFv62NzcICg==`.
- Публичный ключ: `d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a`.

Приватный seed в тестовом README предназначен только для воспроизводимости и запрещён в production.

## Правило тестовых артефактов

Результат не считается доказательством, если отсутствуют исходный unsigned envelope, канонический signing input, digest, signature, participant manifest и negative cases. Эти файлы хранятся вместе и не редактируются по отдельности.

