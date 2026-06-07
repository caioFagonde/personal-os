from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

DANGEROUS_PROMPT_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        # Block rm -rf in any form: rm -rf, rm -fr, rm -r -f, etc. — trailing target is irrelevant
        r"\brm\s+(-rf|-fr|-r\s+-f|-f\s+-r)\b",
        # Also block legacy narrow pattern just in case
        r"\brm\s+-rf\s+/",
        r"\bsudo\b",
        r"\bchmod\s+777\b",
        r"\bcat\s+\.env\b",
        r"\bread\s+\.env\b",
        r"\bprint\s+secrets?\b",
        r"\bexfiltrat",
        r"\btoken\s+dump\b",
        r"\bcredential\s+dump\b",
    ]
]

ALLOWED_MODES = {"analyze", "fix", "feature", "tests", "docs", "refactor"}


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    requires_approval: bool = True


def safe_branch_slug(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower()).strip(".-_")
    return (text or "coding-agent-job")[:80]


def repo_is_allowed(repo_path: str, allowed_roots: list[str]) -> bool:
    repo = Path(repo_path).expanduser().resolve()
    for root in allowed_roots:
        base = Path(root).expanduser().resolve()
        try:
            repo.relative_to(base)
            return True
        except ValueError:
            continue
    return False


def evaluate_prompt(*, prompt: str, mode: str, repo_path: str, allowed_roots: list[str]) -> PolicyDecision:
    if mode not in ALLOWED_MODES:
        return PolicyDecision(False, f"unsupported mode: {mode}")
    if not prompt or len(prompt.strip()) < 8:
        return PolicyDecision(False, "prompt is too short")
    if len(prompt) > 20_000:
        return PolicyDecision(False, "prompt is too large")
    if not repo_is_allowed(repo_path, allowed_roots):
        return PolicyDecision(False, "repo path is outside configured allowlist")
    for pattern in DANGEROUS_PROMPT_PATTERNS:
        if pattern.search(prompt):
            return PolicyDecision(False, f"blocked unsafe prompt pattern: {pattern.pattern}")
    return PolicyDecision(True, "allowed", requires_approval=True)


def build_claude_prompt(*, title: str, prompt: str, mode: str) -> str:
    return f"""# Personal OS Coding Agent Task\n\nMode: {mode}\nTitle: {title}\n\nRules:\n- Work only inside the current git worktree.\n- Do not read, print, modify, or infer secrets from .env, .env.local, credential files, or token stores.\n- Prefer small, reviewable changes.\n- Add or update tests for changed behavior.\n- Return a concise implementation summary, files changed, commands run, and risks.\n- Do not push, deploy, or run destructive commands.\n\nTask:\n{prompt.strip()}\n"""
