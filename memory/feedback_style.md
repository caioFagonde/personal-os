---
name: feedback-style
description: Code style and collaboration preferences observed from this user's project
metadata:
  type: feedback
---

Work in focused, verifiable increments — not large uncontrolled rewrites.

**Why:** The codebase has active work in progress; large rewrites risk introducing regressions and make review harder.

**How to apply:** Make targeted changes, run tests after each batch, and explain what changed and why.

Fix root causes, not symptoms.

**Why:** The user explicitly stated this as a non-negotiable objective.

**How to apply:** Before editing, diagnose the actual failure. Don't add workarounds; trace to the real issue.

Every code change must be backed by tests.

**Why:** Non-negotiable objective stated by user.

**How to apply:** After every new feature or fix, add or update scaffold tests that catch the specific failure class.

Do not read, print, or commit secrets — including .env files.

**Why:** Hard security boundary in CLAUDE.md.

**How to apply:** If a task requires secrets, produce instructions for the user instead.

Before editing: state diagnosis, files to inspect, files to modify, test plan, risk assessment.
After editing: files changed, why each changed, tests run/results, remaining risks, next command.

**Why:** User explicitly requires this format in CLAUDE.md.

**How to apply:** Always follow this structure, even for small changes.
