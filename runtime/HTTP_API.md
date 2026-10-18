# ROZUM HTTP receiver 0.2.0

**Status:** PRE-PRODUCTION / NON-NORMATIVE

**Protocol endpoint:** `POST /v1/messages`

HTTP — адаптер над неизменным пятистадийным receiver. Он не меняет v2.1 signing
input и не добавляет полей в протокольный конверт.

## Запуск

```bash
export ROZUM_KEY_REGISTRY=/secure/config/key-registry.json
export ROZUM_POLICY=config/receiver-policy.v2.1.json
export ROZUM_REPLAY_DB=/var/lib/rozum/replay.sqlite3
export ROZUM_RECEIVER_ID=argos_receiver
export ROZUM_RECEIVER_KEY_ID=manual-errors-v1

rozum serve --host 127.0.0.1 --port 8080
```

По умолчанию сервис слушает только loopback, использует один процесс и требует
постоянный SQLite replay-store. TLS завершается во внешнем reverse proxy. Proxy
headers отключены, пока доверенные прокси явно не спроектированы.

## Transport contract

| Сценарий | HTTP | Тело |
|---|---:|---|
| Принято и атомарно committed | `202` | acknowledgement + пятистадийный trace |
| Malformed/duplicate/non-UTF-8 JSON | `400` | outer `transport_error` без correlation |
| Ошибка подписи, ключа или sender/key binding | `401` | protocol error при безопасной correlation |
| Replay | `409` | protocol error при безопасной correlation |
| Schema/semantic/version/timestamp | `422` | protocol error при безопасной correlation |
| Размер больше лимита | `413` | outer `transport_error` |
| Не `application/json`, не UTF-8 или content encoding | `415` | outer `transport_error` |
| Body read deadline / disconnect | `408` | outer `transport_error` |
| Контролируемая внутренняя ошибка | `500` | generic outer error без exception text |

Служебные endpoints: `GET /healthz` проверяет процесс, а `GET /readyz` также
проверяет доступность replay-store и возвращает `503`, если он недоступен.
OpenAPI/Swagger endpoints отключены. Все ответы содержат
`Cache-Control: no-store`, `nosniff` и `X-ROZUM-Protocol-Version: 2.1`.

## Ограничения

- `ROZUM_MAX_BODY_BYTES` — максимум фактически прочитанных bytes, default `1048576`;
- `ROZUM_BODY_TIMEOUT_SECONDS` — deadline чтения body, default `10`;
- `ROZUM_LIMIT_CONCURRENCY` — предел Uvicorn, default `100`;
- compressed request bodies запрещены;
- JSON с duplicate keys, BOM, `NaN` или `Infinity` запрещён;
- `Content-Length` проверяется заранее, но фактический поток проверяется независимо.

CLI-флаги с теми же именами в kebab-case имеют приоритет над переменными
окружения. Файл `config/service.env.example` содержит только несекретный шаблон.

## Важная граница доверия

Ошибки, для которых безопасно прочитаны входные `id` и `session_id`, возвращаются
как schema-valid ROZUM envelope. В 0.2.0 такой error envelope имеет
`signature: null`; принимающая сторона должна заранее разрешить указанный manual
error channel. Подписанные ответы требуют отдельного outbound keystore/signer и
до его реализации не должны считаться аутентифицированными.

SQLite подходит для одного экземпляра receiver. Горизонтальный запуск требует
общего production replay-store и отдельного нагрузочного/аварийного теста.
