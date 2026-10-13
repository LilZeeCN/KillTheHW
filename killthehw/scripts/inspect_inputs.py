#!/usr/bin/env python3
"""Inventory only explicitly supplied paths and initialize a new homework job."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

from _common import digest, write_json

TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".tsv", ".json", ".html", ".xml",
                   ".py", ".sql", ".java", ".c", ".cpp", ".js", ".tex"}


def kind(path):
    ext = path.suffix.lower()
    if ext in TEXT_EXTENSIONS:
        return "text"
    if ext in {".pdf", ".docx", ".pptx", ".xlsx"}:
        return ext[1:]
    if ext in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".heic"}:
        return "image"
    return "other"


def initialize(directory, inputs):
    root = Path(directory).expanduser().resolve()
    if root.exists():
        raise ValueError(f"Job directory already exists; resume it or choose a new path: {root}")
    files, skipped = set(), []
    for raw in inputs:
        source = Path(raw).expanduser().resolve(strict=True)
        if root.is_relative_to(source) and source.is_dir():
            raise ValueError("Put the job directory outside the supplied input directory")
        if source.is_file():
            files.add(source)
        elif source.is_dir():
            for parent, dirs, names in os.walk(source, followlinks=False):
                for name in list(dirs):
                    candidate = Path(parent) / name
                    if candidate.is_symlink():
                        skipped.append(str(candidate))
                        dirs.remove(name)
                for name in names:
                    candidate = Path(parent) / name
                    if candidate.is_symlink():
                        skipped.append(str(candidate))
                    elif candidate.is_file():
                        files.add(candidate)
    if not files:
        raise ValueError("No regular input files found")
    records = [{"id": f"I{i:03d}", "path": str(path), "kind": kind(path),
                "size": path.stat().st_size, "sha256": digest(path),
                "role": "unclassified", "review": {"status": "pending"}}
               for i, path in enumerate(sorted(files), 1)]
    job = {"schema_version": 1, "job_id": root.name,
           "created_at": datetime.now(timezone.utc).isoformat(),
           "inputs": records, "assignments": [], "requirements": [], "tasks": [],
           "deliverables": [], "checks": [], "issues": [],
           "delivery": {"target": "local", "state": "draft", "scope": ""}}
    root.mkdir(parents=True)
    for name in ("extracted", "evidence", "deliverables"):
        (root / name).mkdir()
    (root / "actions.jsonl").touch()
    write_json(root / "job.json", job)
    return {"job": str(root / "job.json"), "input_count": len(records),
            "skipped_directory_symlinks": skipped,
            "next": "Read requirements, extract materials, and fill the task record."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-dir", required=True)
    parser.add_argument("inputs", nargs="+")
    args = parser.parse_args()
    try:
        print(json.dumps(initialize(args.job_dir, args.inputs), ensure_ascii=False, indent=2))
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
