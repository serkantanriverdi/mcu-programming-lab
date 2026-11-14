# SPDX-License-Identifier: MIT
"""Check Git-visible files for excluded assets and obvious credentials.

This is a release guard, not a legal review or a complete secret detector.
It reports only paths/categories, never the matched secret itself.
"""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
BLOCKED_SUFFIXES = {
    ".exe", ".dll", ".drv", ".enc", ".fmt", ".inc", ".pdf",
    ".zip", ".7z", ".tar", ".gz", ".bin", ".elf", ".eep",
}
BLOCKED_ROOTS = {"vendor", "reverse-engineering", "decoded", "disassembly",
                 "private-archive", "records"}
SECRET = re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
MAGIC = (b"MZ", b"\x7fELF", b"CFG", b"SQLite format 3", b"%PDF")


def inspect(relative, data):
    reasons = []
    if relative.parts[0] in BLOCKED_ROOTS or relative.suffix.lower() in BLOCKED_SUFFIXES:
        reasons.append("excluded publication category")
    if data.startswith(MAGIC):
        reasons.append("binary/vendor-format signature")
    if SECRET.search(data):
        reasons.append("possible credential")
    return reasons


def main():
    result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                            cwd=ROOT, check=True, capture_output=True)
    names = sorted(set(x.decode("utf-8") for x in result.stdout.split(b"\0") if x))
    if not names:
        raise SystemExit("No Git-visible files to inspect")
    failed = []
    for name in names:
        path = ROOT / name
        if path.is_symlink():
            failed.append((name, "symlink requires manual review"))
            continue
        for reason in inspect(Path(name), path.read_bytes()):
            failed.append((name, reason))
    if failed:
        raise SystemExit("Release check failed:\n" + "\n".join(f"{name}: {reason}" for name, reason in failed))
    print(f"PASS: {len(names)} Git-visible files; no excluded asset category or obvious credential found")


if __name__ == "__main__":
    main()
