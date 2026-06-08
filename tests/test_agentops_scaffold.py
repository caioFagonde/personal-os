from __future__ import annotations

import fnmatch
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_agentops_active_json_exists_and_has_p0_tasks():
    active = json.loads((ROOT / ".agents" / "active.json").read_text())
    task_ids = {task["id"] for task in active["tasks"]}
    assert {"ui-foundation", "capture-e2e", "config-validation"}.issubset(task_ids)


def _delegated_path_is_secretish(path: str) -> bool:
    parts = [part.lower() for part in Path(path.replace("\\", "/")).parts]
    if any(part in {".env", "secrets", ".private", "data", "backups", "logs"} for part in parts):
        return True
    basename = parts[-1] if parts else ""
    if basename == ".env.example":
        return False
    patterns = [
        ".env", ".env.*", "*.pem", "*.key", "*.crt", "*.p12", "*.pfx",
        "credentials.json", "client_secret*.json", "*token*.json", "*tokens*.json",
    ]
    return any(fnmatch.fnmatch(basename, pattern) for pattern in patterns)


def test_agentops_tasks_do_not_allow_secret_paths():
    active = json.loads((ROOT / ".agents" / "active.json").read_text())
    for task in active["tasks"]:
        for field in ("allowed_paths", "locked_paths"):
            for path in task.get(field, []):
                assert not _delegated_path_is_secretish(path), f"{task['id']} allows forbidden path {path}"


def test_agentctl_exists_and_is_dependency_free():
    agentctl = ROOT / "scripts" / "agents" / "agentctl.py"
    text = agentctl.read_text()
    assert "argparse" in text
    assert "yaml" not in text.lower(), "agentctl should not require PyYAML for the base path"


def test_codex_and_claude_dispatch_wrappers_exist():
    assert (ROOT / "scripts" / "agents" / "dispatch-claude.sh").exists()
    assert (ROOT / "scripts" / "agents" / "dispatch-codex.sh").exists()
    assert (ROOT / "scripts" / "agents" / "monitor.sh").exists()


def test_agent_docs_exist():
    assert (ROOT / "docs" / "agentops-swarm.md").exists()
    assert (ROOT / "AGENTS.md").exists()


def test_design_tokens_file_is_not_misclassified_as_secret():
    assert not _delegated_path_is_secretish("apps/web/src/design/tokens.ts")


def test_env_example_is_allowed_for_config_validation():
    assert not _delegated_path_is_secretish(".env.example")
