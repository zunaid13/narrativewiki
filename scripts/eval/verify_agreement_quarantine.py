"""Read-only integrity and duplicate scan for the maintainer's artifact quarantine.

No provider calls. Inspect first-party project files, excluding Git objects,
dependencies, EPUB corpora, and Python/pytest caches. Report unreadable paths
explicitly: a partial scan cannot support a claim of exhaustive coverage.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "docs/eval/quarantine_agreement_20261012.json"


def main() -> int:
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    archive = Path(inventory["destination_root"])
    hashes = {entry["sha256"] for entry in inventory["entries"]}
    sizes = {entry["bytes"] for entry in inventory["entries"]}
    failures: list[str] = []
    duplicates: list[str] = []
    unreadable: list[str] = []
    embedded_annotations: list[dict] = []
    for entry in inventory["entries"]:
        destination = archive / entry["destination_relative"]
        try:
            if hashlib.sha256(destination.read_bytes()).hexdigest() != entry["sha256"]:
                failures.append(f"Changed destination: {destination}")
            if Path(entry["source"]).exists():
                failures.append(f"Original source remains: {entry['source']}")
        except OSError as error:
            failures.append(str(error))

    for current, directories, files in os.walk(
        ROOT, onerror=lambda error: unreadable.append(str(error))
    ):
        directories[:] = [
            name for name in directories
            if name not in {".git", "corpus", "node_modules", ".pytest_cache", "__pycache__"}
            and not name.startswith(".venv")
        ]
        for name in files:
            path = Path(current) / name
            relative = path.relative_to(ROOT).as_posix()
            try:
                if path.stat().st_size in sizes:
                    if hashlib.sha256(path.read_bytes()).hexdigest() in hashes:
                        duplicates.append(relative)
                if path.suffix.lower() == ".zip":
                    with zipfile.ZipFile(path) as package:
                        matches = [
                            member for member in package.namelist()
                            if any(token in member.lower() for token in (
                                "human_check/", "human_review/", "agent_annotation/",
                                "accepted_answers.csv", "responses.jsonl", "model_runs/",
                            ))
                        ]
                        if matches:
                            embedded_annotations.append({"path": relative, "members": matches})
            except (OSError, zipfile.BadZipFile) as error:
                unreadable.append(str(error))

    report = {
        "run_id": inventory["run_id"],
        "verified_files": len(inventory["entries"]),
        "integrity_failures": failures,
        "remaining_exact_duplicates": duplicates,
        "remaining_annotation_packages": embedded_annotations,
        "unreadable_paths": unreadable,
        "excluded": ["Git objects/history", "dependencies", "corpus", "Python/pytest caches"],
    }
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return int(bool(failures or duplicates or embedded_annotations or unreadable))


if __name__ == "__main__":
    raise SystemExit(main())
