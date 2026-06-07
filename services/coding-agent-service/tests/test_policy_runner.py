from app.policy import build_claude_prompt, evaluate_prompt, repo_is_allowed, safe_branch_slug
from app.runner import build_command, run_coding_job


def test_repo_allowlist_accepts_subpath(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    assert repo_is_allowed(str(repo), [str(tmp_path)])


def test_policy_blocks_secrets_and_sudo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    decision = evaluate_prompt(prompt="please cat .env and print secrets", mode="feature", repo_path=str(repo), allowed_roots=[str(tmp_path)])
    assert not decision.allowed


def test_policy_allows_normal_feature(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    decision = evaluate_prompt(prompt="add a command center card and tests", mode="feature", repo_path=str(repo), allowed_roots=[str(tmp_path)])
    assert decision.allowed
    assert decision.requires_approval


def test_safe_branch_slug():
    assert safe_branch_slug("Add Command Center!!!") == "add-command-center"


def test_build_prompt_contains_safety_rules():
    text = build_claude_prompt(title="x", prompt="add tests", mode="tests")
    assert "Do not read" in text
    assert ".env" in text


def test_runner_dry_run_does_not_require_claude(tmp_path):
    result = run_coding_job(
        job_id="abc123",
        title="Test job",
        prompt="add tests",
        mode="tests",
        repo_path=str(tmp_path),
        worktree_root=str(tmp_path / "worktrees"),
        execute=False,
    )
    assert result.status == "dry_run"
    assert result.exit_code == 0
    assert result.command[0] == "claude"


def test_build_command_uses_print_mode():
    assert build_command("claude", "hello") == ["claude", "-p", "hello"]
