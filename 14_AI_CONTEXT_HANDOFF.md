# 14 — AI Context Handoff

**Status:** NORMATIVE / ACCEPTED

## Назначение

Этот документ задаёт минимальный пакет, с которым новый ИИ или новый чат может продолжить проект без смешивания нормативной базы и гипотез.

## Порядок загрузки

1. Прочитать `00_MASTER_INDEX.md`.
2. Зафиксировать текущую версию протокола и таблицу статусов.
3. Прочитать `08_SECURITY_DESIGN_DOCUMENT.md` до любых криптографических изменений.
4. Проверить последние записи `12_DECISIONS_LOG.md`.
5. Для утверждений о совместимости изучить реальные артефакты `tests/`, а не только текстовое резюме.
6. Читать `PROPOSED`, `DRAFT` и `NON-NORMATIVE` только после нормативного слоя.

## Минимальный handoff

```yaml
project: Rosum OS
protocol: ROZUM_AI_v2
protocol_version: "2.1"
snapshot_date: "2026-09-02"
normative_security: 08_SECURITY_DESIGN_DOCUMENT.md
decision_log: 12_DECISIONS_LOG.md
validated_test: tests/interoperability/CVT-001/result.json
locked_rules:
  - RFC 8785 JCS
  - Ed25519 RAW-64 Base64
  - five-stage validation pipeline
threading:
  preserve_session_id: true
  reply_to_incoming_id: true
unsigned_rule: "Use signature:null; never fabricate a signature"
```

## Правила продолжения

- Не переписывать историю так, будто более ранний черновик всегда был нормой.
- При конфликте использовать приоритет источников из `00_MASTER_INDEX.md`.
- Любое новое утверждение помечать источником и статусом.
- Любое изменение `LOCKED` оформлять решением и новым тестом.
- Не считать красивый JSON доказательством корректной подписи.
- Не переносить секретный или production key material между чатами.

## Формат межсистемного ответа

При ответе на ROZUM_AI_v2 пакет:

- создать новый `id`;
- установить `reply_to` на входной `id`;
- сохранить `context.session_id`;
- явно описать изменение `context.state`;
- использовать реальную подпись либо `null`;
- отделить результат, допущения и следующий тест.

## Стоп-условия

ИИ должен остановить нормативное изменение, если отсутствует исходный файл, статус неоднозначен, тест нельзя воспроизвести или новое решение противоречит `LOCKED`-документу.

