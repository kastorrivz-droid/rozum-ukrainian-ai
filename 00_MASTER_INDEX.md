# 00 — Master Index

**Project:** Rosum OS  
**Protocol:** ROZUM_AI_v2  
**Working version:** 2.1  
**Snapshot:** 2026-09-02  
**Status:** ACCEPTED / CONTROL DOCUMENT

## Назначение

Этот индекс является точкой входа и картой статусов Knowledge Pack. Пакет восстановлен из последних зафиксированных решений проекта, подтверждённого комплекта `CVT-001` и отдельной ненормативной концептуальной записки.

## Значения статусов

- **NORMATIVE / LOCKED** — обязательный источник истины. Меняется только через решение, версионирование и повторные тесты.
- **VALIDATED** — проверен структурно, тестом или подтверждённым межсистемным прогоном.
- **ACCEPTED** — принят как рабочая архитектурная основа.
- **PROPOSED** — кандидат, ещё не получивший нормативного статуса.
- **DRAFT** — рабочий материал; не должен управлять продакшен-поведением.
- **NON-NORMATIVE** — пояснение, концепт или пример без силы спецификации.

## Реестр модулей

| Файл | Статус | Роль |
|---|---|---|
| `00_MASTER_INDEX.md` | ACCEPTED | Реестр, порядок чтения и статусы |
| `01_ROZUM_VISION.md` | ACCEPTED | Видение, цели и границы |
| `02_ROZUM_AI_v2_SPEC.md` | ACCEPTED / WORKING BASELINE | Конверт и правила протокола 2.1 |
| `03_JSON_SCHEMA.md` | VALIDATED / STRUCTURAL BASELINE | Структурная схема сообщения |
| `04_AGENT_ROLES.md` | ACCEPTED | Канонические роли |
| `05_ARGOS.md` | VALIDATED | Оркестрация и контроль переходов |
| `06_REEVES.md` | PROPOSED | Диалоговый интерфейс |
| `07_ANDROMEDA.md` | PROPOSED | Навигация и архитектурный анализ |
| `08_SECURITY_DESIGN_DOCUMENT.md` | NORMATIVE / LOCKED | Канонический документ безопасности |
| `09_ERROR_PROTOCOL.md` | VALIDATED | Единая модель ошибок |
| `10_API_EXAMPLES.md` | DRAFT / NON-NORMATIVE EXAMPLES | Примеры запросов и ответов |
| `11_TEST_CASES.md` | VALIDATED | Матрица тестов и CVT-001 |
| `12_DECISIONS_LOG.md` | ACCEPTED | Хронология решений |
| `14_AI_CONTEXT_HANDOFF.md` | NORMATIVE / ACCEPTED | Межсистемная передача контекста |
| `15_TWO_LOOP_THINKING_SPEC.md` | INTERNAL / CONCEPT / NON-NORMATIVE | Explore/Validate и калибровка |

Номер `13` зарезервирован и не назначен. В составе — 15 файлов, включая этот индекс.

## Приоритет источников

При противоречии применяется следующий порядок:

1. `08_SECURITY_DESIGN_DOCUMENT.md` и иные документы `NORMATIVE / LOCKED`.
2. Воспроизводимые тестовые артефакты и результаты `PASS`.
3. `12_DECISIONS_LOG.md` по дате и версии.
4. Документы `VALIDATED`, затем `ACCEPTED`.
5. `PROPOSED`, `DRAFT` и `NON-NORMATIVE` — только как материал для рассмотрения.

## Текущая подтверждённая база

- конверт `ROZUM_AI_v2`, версия `2.1`;
- ответ сохраняет `context.session_id` и указывает `reply_to` на `id` входного сообщения;
- при отсутствии реальной подписи передаётся `signature: null`, а не вымышленное значение;
- RFC 8785 JCS обязателен для каноникализации подписываемых структур;
- Ed25519 использует RAW-подпись длиной 64 байта, кодированную Base64;
- обработка безопасности проходит пять стадий: Schema → Semantic → Fast Replay → Crypto → Atomic Commit;
- `tests/interoperability/CVT-001/result.json` фиксирует общий результат `PASS` по шести утверждениям.

