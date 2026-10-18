# 12 — Decisions Log

**Status:** ACCEPTED

## [2026-08-22] Baseline 2.0 / Draft 2.1

- Зафиксирован конверт `ROZUM_AI_v2`.
- `id`/историческое `message_id` — UUIDv4.
- `timestamp` — ISO-8601 UTC с `Z`.
- Для 2.1 уточняются inter-AI threading, безопасность и строгая схема.

## [2026-08-22] Strict RFC 8785

- RFC 8785 JCS принят как обязательный способ каноникализации.
- Ручная имитация через обычный JSON serializer запрещена для production.
- Ранее опубликованные непересчитанные TV-001 digests признаны недействительными.
- Хэши и подписи нельзя генерировать «из головы».

## [2026-08-31] Structural Interoperability

- Версия `2.1` принята для текущего inter-AI обмена.
- Ответ обязан сохранить `context.session_id`.
- Ответ обязан установить `reply_to` на `id` входного пакета.
- При отсутствии реальной криптографии используется `signature: null`.
- Структурный прогон receiver завершён `SUCCESS/PASS`.

## [2026-09-01] Canonical Security Document

- Каноническое имя: `08_SECURITY_DESIGN_DOCUMENT.md`.
- Статус: `NORMATIVE / LOCKED`.
- Исторический `08_SECURITY_SIGNATURE.md` полностью поглощён; параллельная спецификация запрещена.
- Зафиксирован пятистадийный пайплайн: Schema → Semantic → Fast Replay → Crypto → Atomic Commit.

## [2026-09-01] Two-loop Concept Boundary

- Концепт Explore/Validate принят как внутренний материал.
- Статус остаётся `INTERNAL / CONCEPT / NON-NORMATIVE`.
- Сырые идеи не изменяют нормативный слой.

## [2026-09-02] CVT-001

- Сформирован воспроизводимый Ed25519 test bundle.
- Проверены JCS identity, RAW-64 Base64 signature, отказ DER, tamper detection и atomic replay commit.
- Все шесть assertions получили `PASS`.
- Тестовый ключ явно помечен `TEST-ONLY / NON-PRODUCTION`.

## [2026-09-02] Drive Snapshot

- Собран 15-модульный Knowledge Pack.
- Источники: подтверждённые проектные решения, оригинальные байты `CVT-001` и отдельная концептуальная записка.
- Статусы сохранены раздельно; восстановленный snapshot не повышает `PROPOSED/DRAFT` до нормы.

