"""Command-line interface for validation and conformance checks."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .canonical import build_signing_input, sha256_hex
from .conformance import run_cvt001
from .keys import KeyRegistry
from .policy import ReceiverPolicy, parse_utc_timestamp
from .protocol_errors import ReceiverIdentity
from .receiver import Receiver
from .replay import InMemoryReplayStore, SQLiteReplayStore


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be a positive integer")
    return parsed


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be positive")
    return parsed


def _port(value: str) -> int:
    parsed = _positive_int(value)
    if parsed > 65_535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return parsed


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _validate(args: argparse.Namespace) -> int:
    try:
        envelope = _load_json(args.envelope)
        registry = KeyRegistry.from_file(args.registry)
        policy = ReceiverPolicy.from_file(args.policy) if args.policy else ReceiverPolicy()
        replay_store = (
            SQLiteReplayStore(args.replay_db)
            if args.replay_db
            else InMemoryReplayStore()
        )
        receiver = Receiver(registry, policy=policy, replay_store=replay_store)
        now = parse_utc_timestamp(args.now) if args.now else None
        result = receiver.process(envelope, now=now)
        _print_json(result.as_dict())
        return 0 if result.accepted else 2
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        _print_json(
            {
                "accepted": False,
                "state": "CONFIGURATION_ERROR",
                "error": {"message": str(exc), "type": type(exc).__name__},
            }
        )
        return 1


def _cvt001(args: argparse.Namespace) -> int:
    result = run_cvt001(args.bundle)
    _print_json(result)
    return 0 if result["overall_status"] == "PASS" else 2


def _signing_input(args: argparse.Namespace) -> int:
    try:
        envelope = _load_json(args.envelope)
        value = build_signing_input(envelope)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        _print_json({"error": {"message": str(exc), "type": type(exc).__name__}})
        return 1
    _print_json(
        {
            "sha256": sha256_hex(value),
            "utf8": value.decode("utf-8"),
            "byte_length": len(value),
        }
    )
    return 0


def _serve(args: argparse.Namespace) -> int:
    required = {
        "registry": (args.registry, "--registry or ROZUM_KEY_REGISTRY"),
        "policy": (args.policy, "--policy or ROZUM_POLICY"),
        "replay_db": (args.replay_db, "--replay-db or ROZUM_REPLAY_DB"),
        "receiver_id": (args.receiver_id, "--receiver-id or ROZUM_RECEIVER_ID"),
        "receiver_key_id": (
            args.receiver_key_id,
            "--receiver-key-id or ROZUM_RECEIVER_KEY_ID",
        ),
    }
    missing = [description for value, description in required.values() if not value]
    if missing:
        _print_json(
            {
                "accepted": False,
                "state": "CONFIGURATION_ERROR",
                "error": {"message": "Missing required setting: " + ", ".join(missing)},
            }
        )
        return 1

    try:
        import uvicorn

        from .http_api import create_app

        registry = KeyRegistry.from_file(args.registry)
        policy = ReceiverPolicy.from_file(args.policy)
        replay_store = SQLiteReplayStore(args.replay_db)
        receiver = Receiver(registry, policy=policy, replay_store=replay_store)
        identity = ReceiverIdentity(args.receiver_id, args.receiver_key_id)
        app = create_app(
            receiver,
            identity,
            max_body_bytes=args.max_body_bytes,
            body_timeout_seconds=args.body_timeout_seconds,
        )
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            workers=1,
            access_log=not args.no_access_log,
            log_level=args.log_level,
            proxy_headers=False,
            server_header=False,
            limit_concurrency=args.limit_concurrency,
            timeout_keep_alive=5,
            timeout_graceful_shutdown=30,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        _print_json(
            {
                "accepted": False,
                "state": "CONFIGURATION_ERROR",
                "error": {"message": str(exc), "type": type(exc).__name__},
            }
        )
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rozum", description="ROZUM_AI_v2.1 tools")
    subcommands = parser.add_subparsers(dest="command", required=True)

    validate = subcommands.add_parser("validate", help="run the five-stage receiver")
    validate.add_argument("envelope", help="path to an envelope JSON file")
    validate.add_argument("--registry", required=True, help="trusted key registry JSON")
    validate.add_argument("--policy", help="explicit receiver policy JSON")
    validate.add_argument("--replay-db", help="SQLite replay database for persistent mode")
    validate.add_argument("--now", help="test-only injected UTC timestamp ending in Z")
    validate.set_defaults(handler=_validate)

    conformance = subcommands.add_parser("cvt-001", help="reproduce immutable CVT-001")
    conformance.add_argument(
        "--bundle",
        default="tests/interoperability/CVT-001",
        help="path to the CVT-001 bundle",
    )
    conformance.set_defaults(handler=_cvt001)

    signing = subcommands.add_parser("signing-input", help="print canonical v2.1 bytes")
    signing.add_argument("envelope", help="path to an envelope JSON file")
    signing.set_defaults(handler=_signing_input)

    serve = subcommands.add_parser("serve", help="run the bounded HTTP receiver")
    serve.add_argument(
        "--registry",
        default=os.environ.get("ROZUM_KEY_REGISTRY"),
        help="trusted key registry JSON (env: ROZUM_KEY_REGISTRY)",
    )
    serve.add_argument(
        "--policy",
        default=os.environ.get("ROZUM_POLICY"),
        help="explicit receiver policy JSON (env: ROZUM_POLICY)",
    )
    serve.add_argument(
        "--replay-db",
        default=os.environ.get("ROZUM_REPLAY_DB"),
        help="persistent SQLite replay database (env: ROZUM_REPLAY_DB)",
    )
    serve.add_argument(
        "--receiver-id",
        default=os.environ.get("ROZUM_RECEIVER_ID"),
        help="sender_id for protocol errors (env: ROZUM_RECEIVER_ID)",
    )
    serve.add_argument(
        "--receiver-key-id",
        default=os.environ.get("ROZUM_RECEIVER_KEY_ID"),
        help="key_id for protocol errors (env: ROZUM_RECEIVER_KEY_ID)",
    )
    serve.add_argument("--host", default="127.0.0.1", help="bind host (default: loopback)")
    serve.add_argument("--port", type=_port, default=8080)
    serve.add_argument(
        "--max-body-bytes",
        type=_positive_int,
        default=os.environ.get("ROZUM_MAX_BODY_BYTES", "1048576"),
    )
    serve.add_argument(
        "--body-timeout-seconds",
        type=_positive_float,
        default=os.environ.get("ROZUM_BODY_TIMEOUT_SECONDS", "10"),
    )
    serve.add_argument(
        "--limit-concurrency",
        type=_positive_int,
        default=os.environ.get("ROZUM_LIMIT_CONCURRENCY", "100"),
    )
    serve.add_argument(
        "--log-level",
        choices=("critical", "error", "warning", "info", "debug"),
        default="info",
    )
    serve.add_argument("--no-access-log", action="store_true")
    serve.set_defaults(handler=_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    sys.exit(main())
