#!/usr/bin/env python3
"""Verify the immutable Drive snapshot without trusting the working tree layout."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


EXPECTED_ZIP_SHA256 = "f1db4f9784d282693f7dd506b6b4dd7e07c25930ef9e6cd7a89d4d945b512f24"
ZIP_NAME = "Rosum-OS-Knowledge-Pack-v2.1-2026-09-02.zip"


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def parse_manifest(path: Path) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            expected, relative_name = raw_line.split(maxsplit=1)
        except ValueError as exc:
            raise ValueError(f"invalid manifest line {line_number}") from exc
        relative_name = relative_name.lstrip("* ")
        entries.append((expected, relative_name))
    return entries


def safe_path(root: Path, relative_name: str) -> Path:
    candidate = (root / relative_name).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"manifest path escapes repository root: {relative_name}") from exc
    return candidate


def verify(root: Path) -> list[str]:
    failures: list[str] = []
    entries = parse_manifest(root / "MANIFEST.sha256")
    for expected, relative_name in entries:
        path = safe_path(root, relative_name)
        if not path.is_file():
            failures.append(f"missing: {relative_name}")
        elif digest(path) != expected:
            failures.append(f"digest mismatch: {relative_name}")

    archive = root / ZIP_NAME
    if not archive.is_file():
        failures.append(f"missing: {ZIP_NAME}")
    elif digest(archive) != EXPECTED_ZIP_SHA256:
        failures.append(f"digest mismatch: {ZIP_NAME}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the ROZUM v2.1 source snapshot")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    failures = verify(args.root.resolve())
    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    count = len(parse_manifest(args.root / "MANIFEST.sha256"))
    print(f"PASS manifest_entries={count} zip_sha256={EXPECTED_ZIP_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
