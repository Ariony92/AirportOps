"""Consistency checks and synchronization of AirportOps release metadata."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "frontend/package.json"
SEMVER = re.compile(
    r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\Z"
)

# The patterns target release metadata, not historical release notes.
TARGETS = {
    "README.md": re.compile(r"(?m)^(\*\*Version actuelle : V)([^\s]+)( —)"),
    "docs/ROADMAP.md": re.compile(r"(?m)^(# AirportOps — Plan de livraison \(V)([^)]+)(\))"),
    "docs/QUALITY.md": re.compile(r"(?m)^(# AirportOps — Validation technique \(V)([^)]+)(\))"),
    "backend/app/main.py": re.compile(r"(title='AirportOps API',\s*version=')([^']+)(')"),
}
LOCK_ROOT = re.compile(r'(\A\{\s*"name"\s*:\s*"airportops-frontend"\s*,\s*"version"\s*:\s*")[^"]+(?=")')
LOCK_PACKAGE = re.compile(r'("packages"\s*:\s*\{\s*""\s*:\s*\{\s*"name"\s*:\s*"airportops-frontend"\s*,\s*"version"\s*:\s*")[^"]+(?=")')


def canonical_version() -> str:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    version = data["version"]
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        raise ValueError(f"Invalid SemVer in frontend/package.json: {version!r}")
    return version


def update_targets(version: str, sync: bool, problems: list[str]) -> None:
    for relative, pattern in TARGETS.items():
        path = ROOT / relative
        value = path.read_text(encoding="utf-8")
        match = pattern.search(value)
        if not match or len(pattern.findall(value)) != 1:
            problems.append(f"{relative}: release version marker missing or duplicated")
            continue
        current = match.group(2)
        if current == version:
            continue
        if sync:
            revised = value[:match.start(2)] + version + value[match.end(2):]
            path.write_text(revised, encoding="utf-8")
            print(f"Updated {relative}: {current} -> {version}")
        else:
            problems.append(f"{relative}: {current} != {version}")


def update_lock(version: str, sync: bool, problems: list[str]) -> None:
    relative = "frontend/package-lock.json"
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    lock = json.loads(text)
    if lock.get("name") != "airportops-frontend" or lock.get("packages", {}).get("", {}).get("name") != "airportops-frontend":
        problems.append(f"{relative}: unexpected package name")
        return
    root_version = lock.get("version")
    package_version = lock["packages"][""].get("version")
    if root_version == version and package_version == version:
        return
    if not sync:
        problems.append(f"{relative}: root={root_version}, package={package_version}, expected={version}")
        return
    revised, root_count = LOCK_ROOT.subn(lambda match: match.group(1) + version, text)
    revised, package_count = LOCK_PACKAGE.subn(lambda match: match.group(1) + version, revised)
    if root_count != 1 or package_count != 1:
        problems.append(f"{relative}: metadata markers missing or duplicated")
        return
    updated = json.loads(revised)
    if updated["version"] != version or updated["packages"][""]["version"] != version:
        problems.append(f"{relative}: version synchronization failed")
        return
    path.write_text(revised, encoding="utf-8")
    print(f"Updated {relative}: {root_version} / {package_version} -> {version}")


def main() -> int:
    parser = argparse.ArgumentParser(description="AirportOps release metadata consistency")
    command = parser.add_mutually_exclusive_group(required=True)
    command.add_argument("--check", action="store_true", help="Verify release metadata without modifying files")
    command.add_argument("--sync", action="store_true", help="Synchronize metadata from frontend/package.json")
    args = parser.parse_args()

    try:
        version = canonical_version()
        problems: list[str] = []
        update_targets(version, args.sync, problems)
        update_lock(version, args.sync, problems)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Version metadata error: {exc}")
        return 1
    for problem in problems:
        print(f"Version metadata mismatch: {problem}")
    if problems:
        return 1
    print(f"AirportOps release metadata consistent: {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
