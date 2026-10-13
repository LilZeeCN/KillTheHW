#!/usr/bin/env python3
"""Check records, coverage and file versions; this does not grade answers."""
import argparse
import json
from pathlib import Path
import sys

from _common import digest, load_job, local_path


def check_job(root, job):
    problems = []

    def problem(label, message):
        problems.append(f"{label}: {message}")

    def records(key):
        values = job.get(key)
        if not isinstance(values, list) or any(not isinstance(x, dict) for x in values):
            raise ValueError(f"{key} must be an array of objects")
        result = {}
        for value in values:
            identifier = value.get("id")
            if not isinstance(identifier, str) or not identifier or identifier in result:
                raise ValueError(f"{key} has a missing or duplicate id")
            result[identifier] = value
        return result

    inputs, assignments, requirements, tasks, deliverables, checks, issues = (
        records(key) for key in ("inputs", "assignments", "requirements", "tasks",
                                 "deliverables", "checks", "issues"))

    def evidence(label, paths):
        if not isinstance(paths, list) or not paths:
            problem(label, "missing evidence paths")
            return
        for name in paths:
            path = local_path(root, name)
            if not path.is_file() or path.stat().st_size == 0:
                problem(label, f"missing or empty evidence: {name}")

    def subject(label, value):
        path = local_path(root, value.get("path"))
        if not path.is_file():
            problem(label, f"missing file: {value.get('path')}")
        elif not value.get("sha256") or digest(path) != value["sha256"]:
            problem(label, f"stale or missing hash: {value.get('path')}")

    for identifier, item in inputs.items():
        path = Path(item["path"])
        if not path.is_absolute():
            problem(identifier, "input path must be absolute")
        if not path.is_file() or digest(path) != item.get("sha256"):
            problem(identifier, "source is missing or changed")
        review = item.get("review", {})
        if item.get("role") not in {"assignment", "template", "reference", "data", "excluded"}:
            problem(identifier, "input role is unclassified")
        if (review.get("status") != "complete" or review.get("sha256") != item.get("sha256")
                or not review.get("scope")):
            problem(identifier, "source reading/scope is missing or stale")
    if not assignments or not requirements or not tasks:
        problem("coverage", "assignments, requirements and tasks must be recorded")
    for identifier, assignment in assignments.items():
        if not assignment.get("title") or not assignment.get("source"):
            problem(identifier, "assignment title/source missing")

    valid_checks = set()
    for identifier, check in checks.items():
        before = len(problems)
        if check.get("status") != "passed":
            continue
        if not all(check.get(key) for key in ("kind", "method", "result")):
            problem(identifier, "passed check needs kind, method and actual result")
        evidence(identifier, check.get("evidence"))
        if not isinstance(check.get("subjects"), list):
            problem(identifier, "subjects must be an array (empty for online-only work)")
        else:
            for value in check["subjects"]:
                subject(identifier, value)
        hashes = check.get("input_hashes", {})
        if inputs and not hashes:
            problem(identifier, "missing input_hashes for the sources used by this check")
        for input_id, value in hashes.items():
            if input_id not in inputs or inputs[input_id].get("sha256") != value:
                problem(identifier, f"check uses a stale/unknown input: {input_id}")
        if len(problems) == before:
            valid_checks.add(identifier)

    def linked_checks(label, ids):
        if not ids:
            problem(label, "no verification checks linked")
        for identifier in ids:
            if identifier not in valid_checks:
                problem(label, f"check not passed or invalid: {identifier}")
        return [checks[x] for x in ids if x in valid_checks]

    for identifier, task in tasks.items():
        if task.get("selected", True) is False:
            if not task.get("reason"):
                problem(identifier, "unselected task needs a reason")
        elif task.get("status") != "complete":
            problem(identifier, f"task is {task.get('status', 'unrecorded')}")
        for requirement_id in task.get("requirement_ids", []):
            if requirement_id not in requirements:
                problem(identifier, f"unknown requirement: {requirement_id}")
    for identifier, req in requirements.items():
        if req.get("required", True) is False:
            if not req.get("reason"):
                problem(identifier, "optional requirement needs a reason")
            continue
        if req.get("assignment_id") not in assignments or not req.get("source") or not req.get("text"):
            problem(identifier, "requirement text, assignment or source missing")
        ids = req.get("task_ids", [])
        if not ids:
            problem(identifier, "no tasks linked")
        for task_id in ids:
            task = tasks.get(task_id, {})
            if task.get("status") != "complete" or task.get("selected", True) is False:
                problem(identifier, f"required task incomplete/unselected: {task_id}")
        linked = linked_checks(identifier, req.get("check_ids", []))
        if not any(c["kind"] not in {"style", "existence"} for c in linked):
            problem(identifier, "no substantive verification")

    for identifier, item in deliverables.items():
        subject(identifier, item)
        if item.get("status") != "verified":
            problem(identifier, "deliverable has not been verified")
        linked = linked_checks(identifier, item.get("check_ids", []))
        bound = [c for c in linked if any(s.get("path") == item.get("path") and
                 s.get("sha256") == item.get("sha256") for s in c.get("subjects", []))]
        kinds = item.get("required_check_kinds", [])
        if not kinds or all(k in {"style", "existence"} for k in kinds):
            problem(identifier, "required_check_kinds must include substantive verification")
        for kind in kinds:
            if not any(c["kind"] == kind for c in bound):
                problem(identifier, f"missing {kind} check bound to this file version")
        if not item.get("requirement_ids"):
            problem(identifier, "no requirements linked")
        for requirement_id in item.get("requirement_ids", []):
            if requirement_id not in requirements:
                problem(identifier, f"unknown requirement: {requirement_id}")
    for identifier, issue in issues.items():
        if issue.get("blocking", True) and not issue.get("resolved", False):
            problem(identifier, f"unresolved blocker: {issue.get('detail', '')}")

    delivery = job.get("delivery", {})
    target = delivery.get("target")
    allowed = {"local": {"local_ready", "uploaded", "submitted"},
               "upload": {"uploaded", "submitted"}, "submit": {"submitted"}}
    if target not in allowed or delivery.get("state") not in allowed[target]:
        problem("delivery", f"target {target!r} has not been reached; state={delivery.get('state')!r}")
    if target == "local" and not deliverables:
        problem("delivery", "local delivery needs a recorded file (save textual answers as a file)")
    if target in {"upload", "submit"} or delivery.get("state") in {"uploaded", "submitted"}:
        if not delivery.get("scope") or not delivery.get("destination"):
            problem("delivery", "external destination/authorization scope missing")
        receipts = delivery.get("receipts", [])
        valid_receipts = []
        for receipt in receipts:
            expected_states = ({"submitted"} if target == "submit" or delivery.get("state") == "submitted"
                               else {"uploaded", "submitted"})
            if (receipt.get("state") in expected_states and receipt.get("observed_at")
                    and receipt.get("destination") == delivery.get("destination")):
                before = len(problems)
                evidence("receipt", receipt.get("evidence"))
                for value in receipt.get("subjects", []):
                    subject("receipt", value)
                if before == len(problems):
                    valid_receipts.append(receipt)
        if not valid_receipts:
            problem("delivery", "no matching observed receipt")
        for identifier, item in deliverables.items():
            if not any(identifier in r.get("deliverable_ids", []) and any(
                    s.get("path") == item["path"] and s.get("sha256") == item.get("sha256")
                    for s in r.get("subjects", [])) for r in valid_receipts):
                problem("delivery", f"receipt does not cover current version of {identifier}")
    return {"record_checks_passed": not problems, "problems": problems,
            "counts": {"requirements": len(requirements), "tasks": len(tasks),
                       "deliverables": len(deliverables), "valid_checks": len(valid_checks)},
            "note": "Record consistency only; correctness and real UI outcomes require actual verification."}


def format_audit_summary(root, job, result):
    lines = []
    lines.append("=" * 60)
    lines.append("           KillTheHW 实验报告交付预检审计单")
    lines.append("=" * 60)
    counts = result.get("counts", {})
    lines.append(f"【概况】要求: {counts.get('requirements', 0)} 项 | 任务: {counts.get('tasks', 0)} 项 | 交付物: {counts.get('deliverables', 0)} 份 | 有效核验: {counts.get('valid_checks', 0)} 项")

    requirements = {r["id"]: r for r in job.get("requirements", []) if isinstance(r, dict) and "id" in r}
    tasks = {t["id"]: t for t in job.get("tasks", []) if isinstance(t, dict) and "id" in t}
    checks = {c["id"]: c for c in job.get("checks", []) if isinstance(c, dict) and "id" in c}
    deliverables = {d["id"]: d for d in job.get("deliverables", []) if isinstance(d, dict) and "id" in d}

    lines.append("\n【要求与证据覆盖清单】")
    for req_id, req in requirements.items():
        req_text = req.get("text", "未命名要求")
        if len(req_text) > 40:
            req_text = req_text[:37] + "..."
        is_required = req.get("required", True)
        status_tag = "必做" if is_required else "选做"
        lines.append(f"- [{req_id}] ({status_tag}) {req_text}")
        linked_tasks = req.get("task_ids", [])
        for tid in linked_tasks:
            t = tasks.get(tid, {})
            t_status = t.get("status", "unknown")
            lines.append(f"  * 对应任务 [{tid}]: 状态={t_status}")
        linked_checks = req.get("check_ids", [])
        if linked_checks:
            for cid in linked_checks:
                c = checks.get(cid, {})
                c_status = c.get("status", "unknown")
                c_method = c.get("method", "未记录方法")
                evidence = c.get("evidence", [])
                ev_str = f", 证据: {', '.join(evidence)}" if evidence else ""
                lines.append(f"  * 核验 [{cid}]: [{c_status}] {c_method}{ev_str}")
        else:
            lines.append("  * ⚠️ 未关联任何实质核验")

    lines.append("\n【交付物状态】")
    for d_id, d in deliverables.items():
        d_status = d.get("status", "unknown")
        d_path = d.get("path", "unknown")
        req_kinds = d.get("required_check_kinds", [])
        lines.append(f"- [{d_id}] {d_path} (状态: {d_status}, 核验要求: {', '.join(req_kinds)})")

    lines.append("\n【审计结论】")
    if result["record_checks_passed"]:
        lines.append("✅ 预检通过：所有必做要求、任务、核验记录与交付物版本完全一致。")
    else:
        lines.append("❌ 预检未通过，发现以下问题：")
        for prob in result.get("problems", []):
            lines.append(f"  - 🔴 {prob}")
    lines.append("=" * 60)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_dir")
    parser.add_argument("--summary", "--audit", action="store_true", help="Print human-readable audit summary report")
    args = parser.parse_args()
    try:
        root, job = load_job(args.job_dir)
        result = check_job(root, job)
        if args.summary:
            print(format_audit_summary(root, job, result))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["record_checks_passed"] else 1
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

