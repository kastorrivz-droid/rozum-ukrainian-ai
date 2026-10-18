# ROZUM_AI_v2.1 executable receiver

**Status:** IMPLEMENTATION / PRE-PRODUCTION
**Package version:** `0.2.0`
**Normative source:** `08_SECURITY_DESIGN_DOCUMENT.md`

Этот каталог описывает первое исполняемое ядро поверх неизменённого Knowledge Pack. Реализация не повышает свой статус до нормативного и не изменяет формат подписи v2.1.

Чек-лист следующего прогона: [`CVT-002_CHECKLIST.md`](CVT-002_CHECKLIST.md).

## Что реализовано

- пять стадий: Schema → Semantic → Fast Replay → Crypto → Atomic Commit;
- JSON Schema Draft 2020-12 с включённой проверкой `format`;
- RFC 8785 JCS и точное воспроизведение байтов `CVT-001`;
- Ed25519 RAW-64 Base64 и HMAC-SHA256;
- явный `UNSIGNED_ALLOWED` только для заранее внесённого manual channel;
- key/profile registry по паре `(sender_id, key_id)`;
- in-memory и постоянное SQLite replay-хранилище;
- последовательная, конкурентная и restart replay-проверка;
- schema-valid protocol errors и безопасная outer transport error;
- HTTP API с byte limit, body deadline, строгим JSON и постоянным replay-store;
- независимая Node.js JCS-реализация и общие cross-runtime vectors;
- CLI и автоматический тестовый набор.

## Быстрый запуск

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
rozum cvt-001
python -m unittest discover -s tests/runtime -t . -v
node runtime/js-jcs/verify-cvt001.mjs --json
python scripts/verify_snapshot.py
python scripts/check_secrets.py
```

На Windows вместо `source` используется `.venv\\Scripts\\activate`.

## Проверка сообщения

```bash
rozum validate tests/interoperability/CVT-001/envelope.signed.json \\
  --registry config/key-registry.test.json \\
  --policy config/receiver-policy.v2.1.json \\
  --now 2026-08-22T08:50:01Z
```

Для реального процесса добавьте постоянное хранилище:

```bash
rozum validate envelope.json \\
  --registry /secure/path/key-registry.json \\
  --policy config/receiver-policy.v2.1.json \\
  --replay-db /var/lib/rozum/replay.sqlite3
```

## HTTP receiver

```bash
rozum serve \
  --registry /secure/path/key-registry.json \
  --policy config/receiver-policy.v2.1.json \
  --replay-db /var/lib/rozum/replay.sqlite3 \
  --receiver-id argos_receiver \
  --receiver-key-id manual-errors-v1
```

Безопасный bind по умолчанию — `127.0.0.1:8080`. Полный transport contract,
HTTP-коды, лимиты и границы доверия: [`HTTP_API.md`](HTTP_API.md).

## Формат доверенного registry

Ed25519 содержит только публичный ключ:

```json
{
  "sender_id": "agent_id",
  "key_id": "key-v1",
  "profile": "ROZUM-SIG-ED25519",
  "public_key_hex": "RAW_32_BYTE_PUBLIC_KEY_HEX"
}
```

HMAC-секрет не записывается в JSON. Registry указывает имя переменной окружения:

```json
{
  "sender_id": "trusted_peer",
  "key_id": "hmac-v1",
  "profile": "ROZUM-SIG-HMAC-SHA256",
  "secret_env": "ROZUM_HMAC_TRUSTED_PEER_V1"
}
```

## Защитная policy v2.1

Параметры, не закреплённые точными числами в baseline, вынесены в `config/receiver-policy.v2.1.json`:

- максимальный возраст: 300 секунд;
- допустимое будущее рассогласование: 30 секунд;
- replay TTL: 360 секунд;
- `reply_to` должен ссылаться на принятое сообщение той же сессии;
- UUID передаются в каноническом lowercase-виде;
- `:` запрещён в свободных подписываемых scalar-полях.

## Известное ограничение baseline 2.1

Нормативная строка v2.1 не включает `reply_to` и `message_type`. Реализация сохраняет совместимость с LOCKED-документом, поэтому:

- `message_type` не используется для маршрутизации или авторизации;
- `reply_to` проверяется через авторитетное состояние и совпадение сессии;
- криптографическая целостность всего конверта **не заявляется**;
- исправление формата подписи требует новой версии профиля и новых векторов, а не тихой правки v2.1.

## Граница готовности

Это проверяемое ядро с pre-production HTTP transport, а не production-сервис.
До production остаются shared replay storage, outbound signing/production key
management, миграции и наблюдение, независимый второй receiver и полный
`CVT-002`.
