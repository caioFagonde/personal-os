from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .policy import build_claude_prompt, safe_branch_slug


@dataclass(frozen=True)
class RunResult:
    status: str
    command: list[str]
    worktree_path: str | None
    stdout: str
    stderr: str
    exit_code: int | None
    artifacts: list[dict[str, Any]]


def claude_available(command: str = "claude") -> bool:
    return shutil.which(command) is not None


def git_available() -> bool:
    return shutil.which("git") is not None


def build_command(command: str, prompt: str) -> list[str]:
    # Claude Code non-interactive mode is exposed through -p/--print in current CLI docs.
    return [command, "-p", prompt]


def create_worktree(*, repo_path: str, base_dir: str, job_id: str, title: str) -> str:
    repo = Path(repo_path).expanduser().resolve()
    worktrees = Path(base_dir).expanduser().resolve()
    worktrees.mkdir(parents=True, exist_ok=True)
    branch = f"agent/{job_id[:8]}-{safe_branch_slug(title)}"
    target = worktrees / f"job-{job_id}"
    if target.exists():
        return str(target)
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "-B", branch, str(target)], check=True, text=True, capture_output=True, timeout=60)
    return str(target)


def run_coding_job(*, job_id: str, title: str, prompt: str, mode: str, repo_path: str, worktree_root: str, execute: bool, timeout_seconds: int = 900, command: str = "claude") -> RunResult:
    full_prompt = build_claude_prompt(title=title, prompt=prompt, mode=mode)
    if not execute:
        return RunResult(
            status="dry_run",
            command=build_command(command, full_prompt),
            worktree_path=None,
            stdout="Dry run only. Set CODING_AGENT_EXECUTE=true and approve the job to run Claude Code.",
            stderr="",
            exit_code=0,
            artifacts=[{"kind": "prompt", "content": full_prompt}],
        )
    if not git_available():
        return RunResult("failed", ["git"], None, "", "git is not installed", 127, [])
    if not claude_available(command):
        return RunResult("failed", [command], None, "", f"{command} is not installed or not on PATH", 127, [])
    try:
        worktree = create_worktree(repo_path=repo_path, base_dir=worktree_root, job_id=job_id, title=title)
        cmd = build_command(command, full_prompt)
        env = {k: v for k, v in os.environ.items() if not k.endswith("TOKEN") and "SECRET" not in k and "PASSWORD" not in k}
        proc = subprocess.run(cmd, cwd=worktree, text=True, capture_output=True, timeout=timeout_seconds, env=env)
        diff = subprocess.run(["git", "diff", "--stat"], cwd=worktree, text=True, capture_output=True, timeout=30)
        artifacts = [{"kind": "diff_stat", "content": diff.stdout}]
        return RunResult("succeeded" if proc.returncode == 0 else "failed", cmd, worktree, proc.stdout[-20000:], proc.stderr[-20000:], proc.returncode, artifacts)
    except subprocess.TimeoutExpired as exc:
        return RunResult("failed", [command], None, exc.stdout or "", f"timeout after {timeout_seconds}s", 124, [])
    except Exception as exc:
        return RunResult("failed", [command], None, "", str(exc), 1, [])
