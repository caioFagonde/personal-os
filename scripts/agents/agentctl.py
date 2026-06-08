#!/usr/bin/env python3
"""Personal OS AgentOps controller.

This is a conservative orchestration helper for running Claude Code/Codex workers
in isolated git worktrees. It does not call any remote API itself.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ACTIVE_JSON = ROOT / ".agents" / "active.json"
RUN_ROOT = ROOT / ".agents" / "runs"
REPORT_ROOT = ROOT / ".agents" / "reports"
WORKTREE_ROOT = ROOT / ".agent-worktrees"

FORBIDDEN_PATH_PARTS = {".env", "secrets", ".private", "data", "backups", "logs"}
FORBIDDEN_BASENAME_PATTERNS = [
    ".env", ".env.*", "*.pem", "*.key", "*.crt", "*.p12", "*.pfx",
    "credentials.json", "client_secret*.json", "*token*.json", "*tokens*.json",
]


def run(cmd: list[str], cwd: Path | None = None, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd or ROOT), check=check, text=True, capture_output=capture)


def load_active() -> dict[str, Any]:
    if not ACTIVE_JSON.exists():
        raise SystemExit(f"Missing {ACTIVE_JSON}. Apply the AgentOps kit first.")
    return json.loads(ACTIVE_JSON.read_text(encoding="utf-8"))


def tasks(active: dict[str, Any]) -> list[dict[str, Any]]:
    return list(active.get("tasks", []))


def task_by_id(task_id: str) -> dict[str, Any]:
    active = load_active()
    for t in tasks(active):
        if t["id"] == task_id:
            return t
    raise SystemExit(f"Unknown task id: {task_id}")


def safe_relpath(path: str) -> bool:
    """Return True if a task path is safe to delegate.

    This intentionally checks path components and secret-looking filenames rather
    than arbitrary substrings. For example, `apps/web/src/design/tokens.ts` is a
    legitimate design-token file and must not be rejected merely because it
    contains the substring "token".
    """
    p = path.replace("\\", "/").strip()
    if p.startswith("/") or ".." in Path(p).parts:
        return False
    parts = [part.lower() for part in Path(p).parts]
    if any(part in FORBIDDEN_PATH_PARTS for part in parts):
        return False
    basename = parts[-1] if parts else ""
    if basename == ".env.example":
        return True
    return not any(fnmatch.fnmatch(basename, pattern) for pattern in FORBIDDEN_BASENAME_PATTERNS)


def task_report_candidates(task_id: str) -> list[Path]:
    """Report locations in priority order.

    Some interactive agents write the requested report inside their isolated
    worktree (`.agent-worktrees/<task>/.agents/reports/<task>/report.md`) rather
    than the controller repo. We accept and collect both.
    """
    return [
        REPORT_ROOT / task_id / "report.md",
        worktree_path(task_id) / ".agents" / "reports" / task_id / "report.md",
    ]


def first_existing_report(task_id: str) -> Path | None:
    for candidate in task_report_candidates(task_id):
        if candidate.exists():
            return candidate
    return None


def ensure_dirs() -> None:
    for p in [RUN_ROOT, REPORT_ROOT, WORKTREE_ROOT, ROOT / ".agents" / "state"]:
        p.mkdir(parents=True, exist_ok=True)


def cmd_init(args: argparse.Namespace) -> None:
    ensure_dirs()
    print("✓ AgentOps directories ready")
    print(f"  worktrees: {WORKTREE_ROOT}")
    print(f"  runs:      {RUN_ROOT}")
    print(f"  reports:   {REPORT_ROOT}")


def cmd_doctor(args: argparse.Namespace) -> None:
    ensure_dirs()
    print("AgentOps doctor")
    print("---------------")
    for name in ["git", "python3"]:
        print(f"{name:10} {'ok' if shutil.which(name) else 'missing'}")
    for name in ["claude", "codex", "docker", "pnpm"]:
        print(f"{name:10} {'ok' if shutil.which(name) else 'missing/optional'}")
    try:
        out = run(["git", "status", "--short"], capture=True).stdout.strip()
        print("git        ok")
        if out:
            print("⚠ working tree has changes. Worktrees are still allowed, but commit/stash before integration.")
            for line in out.splitlines()[:20]:
                print("  ", line)
    except Exception as exc:
        print(f"git        error: {exc}")
    active = load_active()
    print(f"tasks      {len(tasks(active))}")
    bad = []
    for t in tasks(active):
        for p in t.get("allowed_paths", []) + t.get("locked_paths", []):
            if not safe_relpath(p):
                bad.append((t["id"], p))
    if bad:
        print("✗ forbidden-looking task paths:")
        for tid, p in bad:
            print(f"  {tid}: {p}")
        raise SystemExit(2)
    print("path guard ok")


def cmd_list(args: argparse.Namespace) -> None:
    active = load_active()
    for t in tasks(active):
        deps = ",".join(t.get("depends_on", [])) or "-"
        print(f"{t['id']:28} {t.get('priority',''):3} {t.get('executor',''):16} deps={deps}")
        print(f"  {t.get('title','')}")


def worktree_path(task_id: str) -> Path:
    return WORKTREE_ROOT / task_id


def branch_name(task_id: str) -> str:
    return f"agent/{task_id}"


def cmd_create_worktree(args: argparse.Namespace) -> None:
    task = task_by_id(args.task_id)
    ensure_dirs()
    wt = worktree_path(task["id"])
    if wt.exists():
        print(f"✓ worktree already exists: {wt}")
        return
    run(["git", "worktree", "add", str(wt), "-b", branch_name(task["id"])])
    print(f"✓ created worktree: {wt}")
    print(f"  branch: {branch_name(task['id'])}")


def compose_prompt(task: dict[str, Any]) -> str:
    role_file = load_active().get("workers", {}).get(task.get("executor"), {}).get("role_file")
    role_text = ""
    if role_file and (ROOT / role_file).exists():
        role_text = (ROOT / role_file).read_text(encoding="utf-8")
    task_file = ROOT / task.get("prompt_file", "")
    task_text = task_file.read_text(encoding="utf-8") if task_file.exists() else json.dumps(task, indent=2)
    return f"""# Personal OS AgentOps Task: {task['id']}

Repository root: {ROOT}
Worktree path: {worktree_path(task['id'])}
Branch: {branch_name(task['id'])}

## Role

{role_text}

## Task contract

{task_text}

## Machine-readable task metadata

```json
{json.dumps(task, indent=2)}
```

## Required final report

Write a final report before stopping. Preferred location in the worktree:

`.agents/reports/{task['id']}/report.md`

The controller will also collect it from:

`{REPORT_ROOT / task['id'] / 'report.md'}`

Include:
1. Root cause / diagnosis.
2. Files changed.
3. Tests run and exact results.
4. Acceptance criteria status.
5. Remaining risks.
6. Follow-up task suggestions.

If blocked, do not broaden scope. Write the blocker and exact command/output needed.
"""


def write_prompt(task_id: str) -> Path:
    task = task_by_id(task_id)
    ensure_dirs()
    run_dir = RUN_ROOT / task_id
    run_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = run_dir / "PROMPT.md"
    prompt_path.write_text(compose_prompt(task), encoding="utf-8")
    print(prompt_path)
    return prompt_path


def cmd_prompt(args: argparse.Namespace) -> None:
    path = write_prompt(args.task_id)
    if args.print:
        print(path.read_text(encoding="utf-8"))


def cmd_dispatch(args: argparse.Namespace) -> None:
    task = task_by_id(args.task_id)
    ensure_dirs()
    if not worktree_path(task["id"]).exists():
        cmd_create_worktree(argparse.Namespace(task_id=task["id"]))
    prompt_path = write_prompt(task["id"])
    wt = worktree_path(task["id"])
    report_dir = REPORT_ROOT / task["id"]
    report_dir.mkdir(parents=True, exist_ok=True)
    log_path = report_dir / f"{args.engine}-{args.mode}.log"

    if args.engine == "claude":
        if not shutil.which("claude"):
            raise SystemExit("claude command not found. Install/login first.")
        if args.mode == "headless":
            # Claude Code supports -p/--print for non-interactive runs.
            cmd = f"cd {shlex.quote(str(wt))} && claude -p < {shlex.quote(str(prompt_path))} 2>&1 | tee {shlex.quote(str(log_path))}"
        else:
            cmd = f"cd {shlex.quote(str(wt))} && printf '%s\n' 'Prompt file: {prompt_path}' && claude"
    elif args.engine == "codex":
        if not shutil.which("codex"):
            raise SystemExit("codex command not found. Install/login first.")
        if args.mode == "headless":
            # Codex CLI documents `codex exec` and stdin prompt via `-`.
            cmd = f"codex exec --cd {shlex.quote(str(wt))} --sandbox workspace-write --ask-for-approval never - < {shlex.quote(str(prompt_path))} 2>&1 | tee {shlex.quote(str(log_path))}"
        else:
            cmd = f"codex --cd {shlex.quote(str(wt))} --sandbox workspace-write --ask-for-approval on-request \"$(cat {shlex.quote(str(prompt_path))})\""
    else:
        raise SystemExit("engine must be claude or codex")

    print("Dispatch command:")
    print(cmd)
    if args.dry_run:
        return
    os.execvp("bash", ["bash", "-lc", cmd])


def cmd_status(args: argparse.Namespace) -> None:
    active = load_active()
    print("AgentOps status")
    print("---------------")
    for t in tasks(active):
        tid = t["id"]
        wt = worktree_path(tid)
        report = first_existing_report(tid)
        wt_status = "worktree" if wt.exists() else "no-worktree"
        report_status = "report" if report else "no-report"
        branch = branch_name(tid)
        dirty = ""
        if wt.exists():
            try:
                s = run(["git", "status", "--short"], cwd=wt, capture=True).stdout.strip()
                dirty = "dirty" if s else "clean"
            except Exception:
                dirty = "unknown"
        print(f"{tid:28} {t.get('priority',''):3} {wt_status:12} {dirty:7} {report_status:10} {branch}")


def cmd_collect(args: argparse.Namespace) -> None:
    active = load_active()
    out = ["# AgentOps Tranche Report", ""]
    for t in tasks(active):
        tid = t["id"]
        report = first_existing_report(tid)
        out.append(f"## {tid}")
        out.append("")
        if report:
            canonical = REPORT_ROOT / tid / "report.md"
            canonical.parent.mkdir(parents=True, exist_ok=True)
            if report != canonical:
                canonical.write_text(report.read_text(encoding="utf-8"), encoding="utf-8")
            out.append(canonical.read_text(encoding="utf-8"))
        else:
            out.append("No report yet.")
        out.append("")
    dest = ROOT / ".agents" / "reports" / "TRANCHE_REPORT.md"
    dest.write_text("\n".join(out), encoding="utf-8")
    print(dest)


def cmd_diff(args: argparse.Namespace) -> None:
    task = task_by_id(args.task_id)
    wt = worktree_path(task["id"])
    if not wt.exists():
        raise SystemExit(f"No worktree for {task['id']}")
    print(run(["git", "diff", "--stat"], cwd=wt, capture=True).stdout)
    print(run(["git", "status", "--short"], cwd=wt, capture=True).stdout)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Personal OS AgentOps controller")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init").set_defaults(func=cmd_init)
    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    sub.add_parser("list").set_defaults(func=cmd_list)
    sp = sub.add_parser("create-worktree"); sp.add_argument("task_id"); sp.set_defaults(func=cmd_create_worktree)
    sp = sub.add_parser("prompt"); sp.add_argument("task_id"); sp.add_argument("--print", action="store_true"); sp.set_defaults(func=cmd_prompt)
    sp = sub.add_parser("dispatch"); sp.add_argument("task_id"); sp.add_argument("--engine", choices=["claude","codex"], required=True); sp.add_argument("--mode", choices=["interactive","headless"], default="interactive"); sp.add_argument("--dry-run", action="store_true"); sp.set_defaults(func=cmd_dispatch)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("collect").set_defaults(func=cmd_collect)
    sp = sub.add_parser("diff"); sp.add_argument("task_id"); sp.set_defaults(func=cmd_diff)
    return p


def main() -> None:
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
