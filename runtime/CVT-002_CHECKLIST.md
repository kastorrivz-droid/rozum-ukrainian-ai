# CVT-002 — Receiver + Interoperability checklist

**Status:** IMPLEMENTATION CHECKLIST / NON-NORMATIVE
**Baseline:** ROZUM_AI_v2.1 snapshot 2026-09-02

## Уже закрыто исполняемым ядром 0.2.0

- [x] Exact protocol/version, обязательные поля и запрет лишних top-level полей.
- [x] JSON Schema 2020-12 с активной `format`-проверкой.
- [x] UUIDv4 и canonical lowercase policy для `id`/`reply_to`.
- [x] Настраиваемые timestamp window, skew и replay TTL.
- [x] Registry `(sender_id, key_id) → profile/key/status`.
- [x] RFC 8785 JCS и точное воспроизведение `CVT-001`.
- [x] Ed25519 RAW-64 Base64 и HMAC-SHA256 positive/negative/rotation tests.
- [x] `SIGNATURE_REQUIRED` для strict channel и отдельный `UNSIGNED_ALLOWED` для manual channel.
- [x] Bloom/cache hit используется только как hint; authoritative miss продолжает Stage 4.
- [x] Atomic SQLite replay: sequential duplicate, concurrent race и restart.
- [x] Crypto failure не резервирует `id`.
- [x] Новый response `id`, известный `reply_to` и совпадение `session_id`.
- [x] Schema-valid protocol error и outer transport error при небезопасной correlation.
- [x] Защитный запрет `:` в свободных scalar-полях подписываемой строки v2.1.
- [x] Характеризационный тест подтверждает, что `reply_to` и `message_type` не подписаны в v2.1.
- [x] HTTP `POST /v1/messages`: `202/400/401/408/409/413/415/422/500` contract.
- [x] Фактический streaming byte limit и отдельная проверка `Content-Length`.
- [x] Body deadline, запрет compression и strict UTF-8 JSON без duplicate keys/NaN/BOM.
- [x] Безопасные transport errors без утечки exception text и без ложной correlation.
- [x] Постоянный SQLite replay-store обязателен для `rozum serve`; bind по умолчанию loopback.
- [x] Независимый Node.js JCS runtime совпадает с Python на общих vectors и `CVT-001` bytes.
- [x] CI исполняет Python matrix и отдельный Node.js 24 cross-runtime job.
- [x] CI проверяет текущий tracked tree и вложенный ZIP на распространённые credential patterns.

## Нужно закрыть до заявления полного CVT-002 PASS

- [ ] Утвердить версионированное решение для криптографической привязки `reply_to` и `message_type`; v2.1 тихо не менять.
- [ ] Утвердить постоянный production registry, ротацию и отзыв ключей.
- [ ] Добавить независимую вторую реализацию полного receiver (JCS subset уже закрыт).
- [ ] Добавить queue transport и определить ack/redelivery/dead-letter semantics (HTTP закрыт).
- [ ] Добавить outbound keystore/signer для аутентифицированных protocol-error responses.
- [ ] Проверить TLS/reverse-proxy deployment и политику доверенных proxy headers.
- [ ] Сохранить отдельные request/response/error fixtures и trace каждого case.
- [ ] Добавить crash-after-commit тест и доказать различие `COMMITTED`, `DISPATCHED`, `COMPLETED`.
- [ ] Выполнить полный набор tamper-тестов для каждого подписанного scalar, `context`, `data`, `question`, `output_format`.
- [ ] Провести нагрузочный concurrent replay test в целевом production storage.
- [ ] Провести независимый inter-AI прогон минимум с двумя участниками и отдельными manifests.
- [ ] Только после полного PASS обновить `11_TEST_CASES.md`, `12_DECISIONS_LOG.md`, `00_MASTER_INDEX.md` и `14_AI_CONTEXT_HANDOFF.md`.

## Критерий следующего прогона

`GO` для следующего **PRE-CVT-002** прогона, когда CI зелёный, snapshot checksum
совпадает, tracked-tree secrets scan чистый, Python/Node JCS bytes совпадают и
HTTP fixtures имеют ожидаемые коды/ошибки. Полный `CVT-002 PASS` запрещено
заявлять, пока остаётся хотя бы один незакрытый пункт выше.
