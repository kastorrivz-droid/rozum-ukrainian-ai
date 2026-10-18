#!/usr/bin/env python3
"""Fail when common credential forms appear in Git-tracked files."""

from __future__ import annotations

import re
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "GitHub token": re.compile(
        rb"(?:gh[pousr]_[A-Za-z0-9]{30,255}|github_pat_[A-Za-z0-9_]{50,255})"
    ),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS access key": re.compile(rb"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    "Slack token": re.compile(rb"xox[baprs]-[A-Za-z0-9-]{20,}"),
}


def tracked_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
    )
    return [ROOT / item.decode("utf-8") for item in output.split(b"\0") if item]


def findings_in(data: bytes, location: str) -> list[str]:
    return [f"{location}: possible {name}" for name, pattern in PATTERNS.items() if pattern.search(data)]


def scan(path: Path) -> list[str]:
    findings = findings_in(path.read_bytes(), str(path.relative_to(ROOT)))
    if path.suffix.lower() != ".zip":
        return findings
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            findings.extend(
                findings_in(
                    archive.read(member),
                    f"{path.relative_to(ROOT)}!{member.filename}",
                )
            )
    return findings


def main() -> int:
    paths = tracked_files()
    findings = [finding for path in paths for finding in scan(path)]
    if findings:
        print("Credential-pattern scan: FAIL", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1
    print(f"Credential-pattern scan: PASS ({len(paths)} tracked files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
