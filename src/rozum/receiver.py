"""Five-stage ROZUM_AI_v2.1 receiver pipeline."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from typing import Any

from .crypto import verify_signature
from .errors import ErrorCode, ProcessResult, ProtocolViolation, TraceEntry
from .keys import KeyRegistry
from .policy import ReceiverPolicy
from .replay import (
    FastReplayCache,
    InMemoryFastReplayCache,
    InMemoryReplayStore,
    ReplayStore,
)
from .schema import SchemaValidator


STAGE_NAMES = {
    1: "Schema Validation",
    2: "Semantic Check",
    3: "Fast Replay Pre-Check",
    4: "Cryptographic Verification",
    5: "Atomic Replay Store Commit",
}


class Receiver:
    def __init__(
        self,
        registry: KeyRegistry,
        *,
        policy: ReceiverPolicy | None = None,
        replay_store: ReplayStore | None = None,
        fast_replay_cache: FastReplayCache | None = None,
        schema_validator: SchemaValidator | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.registry = registry
        self.policy = policy or ReceiverPolicy()
        self.replay_store = replay_store or InMemoryReplayStore()
        self.fast_replay_cache = fast_replay_cache or InMemoryFastReplayCache()
        self.schema_validator = schema_validator or SchemaValidator()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    @staticmethod
    def _failure(
        trace: list[TraceEntry],
        violation: ProtocolViolation,
        *,
        crypto_status: str | None = None,
    ) -> ProcessResult:
        if isinstance(violation.stage, int) and not any(
            entry.stage == violation.stage and entry.status == "FAIL" for entry in trace
        ):
            trace.append(
                TraceEntry(
                    violation.stage,
                    STAGE_NAMES[violation.stage],
                    "FAIL",
                    (violation.code.value,),
                )
            )
        return ProcessResult(
            accepted=False,
            state="REJECTED",
            crypto_status=crypto_status,
            trace=tuple(trace),
            error=violation,
        )

    def process(
        self,
        envelope: Mapping[str, Any] | Any,
        *,
        now: datetime | None = None,
    ) -> ProcessResult:
        trace: list[TraceEntry] = []

        if isinstance(envelope, Mapping) and envelope.get("protocol_version") not in (
            None,
            "2.1",
        ):
            return self._failure(
                trace,
                ProtocolViolation(
                    ErrorCode.UNSUPPORTED_PROTOCOL_VERSION,
                    1,
                    "The receiver supports only protocol version 2.1",
                ),
            )

        try:
            self.schema_validator.validate(envelope)
        except ProtocolViolation as violation:
            return self._failure(trace, violation)
        trace.append(
            TraceEntry(
                1,
                STAGE_NAMES[1],
                "PASS",
                ("draft_2020_12", "format_assertion", "required_fields"),
            )
        )

        assert isinstance(envelope, Mapping)
        materialized = dict(envelope)
        check_time = now or self.clock()
        if check_time.tzinfo is None:
            check_time = check_time.replace(tzinfo=timezone.utc)
        check_time = check_time.astimezone(timezone.utc)

        try:
            self.policy.validate(materialized, check_time)
            owners = self.registry.owners_for_key_id(materialized["key_id"])
            if owners and materialized["sender_id"] not in owners:
                raise ProtocolViolation(
                    ErrorCode.SENDER_KEY_MISMATCH,
                    2,
                    "key_id is registered to a different sender",
                )

            reply_to = materialized["reply_to"]
            if reply_to is not None and self.policy.require_known_reply:
                parent = self.replay_store.get(reply_to, check_time)
                if parent is None:
                    raise ProtocolViolation(
                        ErrorCode.SEMANTIC_INVALID,
                        2,
                        "reply_to does not reference an accepted message",
                        details={"rule": "known_reply_to"},
                    )
                if parent.session_id != materialized["context"]["session_id"]:
                    raise ProtocolViolation(
                        ErrorCode.SEMANTIC_INVALID,
                        2,
                        "reply_to belongs to a different session",
                        details={"rule": "reply_session_match"},
                    )
        except ProtocolViolation as violation:
            return self._failure(trace, violation)
        trace.append(
            TraceEntry(
                2,
                STAGE_NAMES[2],
                "PASS",
                ("timestamp_window", "policy_allowlists", "sender_key_binding"),
            )
        )

        message_id = materialized["id"]
        fast_hit = self.fast_replay_cache.might_contain(message_id)
        if fast_hit:
            authoritative = self.replay_store.get(message_id, check_time)
            if authoritative is not None:
                trace.append(
                    TraceEntry(
                        3,
                        STAGE_NAMES[3],
                        "PASS",
                        ("fast_hit", "authoritative_conflict_confirmed"),
                    )
                )
                return self._failure(
                    trace,
                    ProtocolViolation(
                        ErrorCode.REPLAY_CONFLICT,
                        5,
                        "Message id is already committed",
                    ),
                )
            replay_checks = ("fast_hit", "authoritative_miss", "continue_to_crypto")
        else:
            replay_checks = ("fast_miss", "continue_to_crypto")
        trace.append(TraceEntry(3, STAGE_NAMES[3], "PASS", replay_checks))

        record = self.registry.resolve(materialized["sender_id"], materialized["key_id"])
        try:
            crypto_status = verify_signature(materialized, record)
        except ProtocolViolation as violation:
            return self._failure(trace, violation)
        trace.append(
            TraceEntry(
                4,
                STAGE_NAMES[4],
                "UNSIGNED_ALLOWED" if crypto_status == "UNSIGNED_ALLOWED" else "PASS",
                (
                    "preauthorized_manual_channel"
                    if crypto_status == "UNSIGNED_ALLOWED"
                    else "signature_verified",
                ),
            )
        )

        committed = self.replay_store.commit(
            message_id,
            materialized["context"]["session_id"],
            check_time,
            self.policy.replay_ttl,
        )
        if not committed:
            return self._failure(
                trace,
                ProtocolViolation(
                    ErrorCode.REPLAY_CONFLICT,
                    5,
                    "Message id lost the atomic replay commit race",
                ),
                crypto_status=crypto_status,
            )
        self.fast_replay_cache.add(message_id)
        trace.append(
            TraceEntry(5, STAGE_NAMES[5], "PASS", ("atomic_unique_commit",))
        )
        return ProcessResult(
            accepted=True,
            state="COMMITTED",
            crypto_status=crypto_status,
            trace=tuple(trace),
        )
