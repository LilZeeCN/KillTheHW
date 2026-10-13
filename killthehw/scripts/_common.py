"""File and JSON helpers shared by the local homework tools."""
import hashlib
import json
import os
from pathlib import Path
import tempfile


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, data):
    path = Path(path)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     delete=False) as stream:
        temp = Path(stream.name)
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def load_job(directory):
    root = Path(directory).expanduser().resolve()
    job = json.loads((root / "job.json").read_text(encoding="utf-8"))
    if job.get("schema_version") != 1:
        raise ValueError("Unsupported or missing schema_version (expected 1)")
    return root, job


def local_path(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError(f"Expected a task-relative path: {relative!r}")
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path leaves task directory: {relative}")
    return path


import contextlib
import subprocess


@contextlib.contextmanager
def caffeinate_guard(flags="-dimsu"):
    """Context manager to prevent system sleep, display sleep and idle timeout during automated execution.
    Automatically spawns `caffeinate` and cleans it up on exit.
    """
    proc = None
    try:
        # -d: create display assertion
        # -i: create idle assertion
        # -m: create disk assertion
        # -s: create system assertion
        # -u: declare user activity
        proc = subprocess.Popen(["caffeinate", flags, "-w", str(os.getpid())])
    except Exception:
        pass  # Non-fatal if caffeinate is not present or non-macOS

    try:
        yield proc
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except Exception:
                proc.kill()

