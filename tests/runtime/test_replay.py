from __future__ import annotations

import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from rozum.errors import ErrorCode
from rozum.receiver import Receiver
from rozum.replay import InMemoryFastReplayCache, InMemoryReplayStore, SQLiteReplayStore

from .common import cvt_now, cvt_registry, load_json


class AlwaysHitCache:
    def might_contain(self, message_id: str) -> bool:
        return True

    def add(self, message_id: str) -> None:
        return None


class ReplayTests(unittest.TestCase):
    def test_fast_false_positive_continues_to_crypto_and_commit(self) -> None:
        receiver = Receiver(
            cvt_registry(),
            replay_store=InMemoryReplayStore(),
            fast_replay_cache=AlwaysHitCache(),
        )
        result = receiver.process(load_json("envelope.signed.json"), now=cvt_now())
        self.assertTrue(result.accepted)
        stage_three = next(entry for entry in result.trace if entry.stage == 3)
        self.assertIn("authoritative_miss", stage_three.checks)
        self.assertIn("continue_to_crypto", stage_three.checks)

    def test_fast_cache_is_bounded_and_eviction_is_only_a_false_negative(self) -> None:
        cache = InMemoryFastReplayCache(max_entries=2)
        cache.add("first")
        cache.add("second")
        cache.add("third")
        self.assertFalse(cache.might_contain("first"))
        self.assertTrue(cache.might_contain("second"))
        self.assertTrue(cache.might_contain("third"))

    def test_crypto_failure_does_not_reserve_message_id(self) -> None:
        receiver = Receiver(cvt_registry())
        failed = receiver.process(
            load_json("negative_cases/tampered_envelope.json"), now=cvt_now()
        )
        accepted = receiver.process(load_json("envelope.signed.json"), now=cvt_now())
        self.assertEqual(failed.error.code, ErrorCode.SIGNATURE_VERIFICATION_FAILED)
        self.assertTrue(accepted.accepted)

    def test_sequential_duplicate_is_rejected(self) -> None:
        receiver = Receiver(cvt_registry())
        envelope = load_json("envelope.signed.json")
        self.assertTrue(receiver.process(envelope, now=cvt_now()).accepted)
        duplicate = receiver.process(envelope, now=cvt_now())
        self.assertEqual(duplicate.error.code, ErrorCode.REPLAY_CONFLICT)

    def test_sqlite_store_survives_receiver_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "replay.sqlite3"
            envelope = load_json("envelope.signed.json")
            first = Receiver(
                cvt_registry(),
                replay_store=SQLiteReplayStore(database),
            )
            self.assertTrue(first.process(envelope, now=cvt_now()).accepted)

            restarted = Receiver(
                cvt_registry(),
                replay_store=SQLiteReplayStore(database),
                fast_replay_cache=InMemoryFastReplayCache(),
            )
            duplicate = restarted.process(envelope, now=cvt_now())
            self.assertEqual(duplicate.error.code, ErrorCode.REPLAY_CONFLICT)
            self.assertEqual(duplicate.error.stage, 5)

    def test_concurrent_atomic_commit_has_exactly_one_winner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "replay.sqlite3"
            receiver = Receiver(
                cvt_registry(),
                replay_store=SQLiteReplayStore(database),
            )
            envelope = load_json("envelope.signed.json")

            def attempt(_index: int):
                return receiver.process(envelope, now=cvt_now())

            with ThreadPoolExecutor(max_workers=8) as executor:
                results = list(executor.map(attempt, range(8)))

            accepted = [result for result in results if result.accepted]
            rejected = [result for result in results if not result.accepted]
            self.assertEqual(len(accepted), 1)
            self.assertEqual(len(rejected), 7)
            self.assertTrue(
                all(result.error.code is ErrorCode.REPLAY_CONFLICT for result in rejected)
            )


if __name__ == "__main__":
    unittest.main()
