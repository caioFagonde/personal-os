You are the automatic QA repair node for Personal OS.

You are running inside an isolated git worktree.

Task:
Fix the concrete test/check failure below. Do not add broad new features. Do not perform unrelated refactors. Make the smallest correct change that satisfies the failing tests and preserves product intent.

Hard security rules:
- Do not read, print, modify, or commit .env, .env.*, secrets/, data/, backups/, logs/, credentials, tokens, OAuth secrets, private keys, or personal data.
- Do not weaken auth/security.
- Do not add arbitrary remote shell.
- Do not run destructive commands.
- Do not commit or push to remote.
- Do not hide test failures by deleting meaningful tests.
- If a test is wrong, update it only with a precise justification and maintain the intended invariant.

Failed command:
```bash
run_checks_raw
```

Failure output:
```text

===== Running checks =====
...................................................F.................... [ 27%]
........................................................................ [ 55%]
........................................................................ [ 83%]
.........................F.FFF...........ss                              [100%]
=================================== FAILURES ===================================
___________ test_gateway_config_contract_is_actionable_and_redacted ____________

    def test_gateway_config_contract_is_actionable_and_redacted():
        config = (ROOT / "services/api-gateway/app/config_validation.py").read_text()
        main = (ROOT / "services/api-gateway/app/main.py").read_text()
        assert '"masked": "********"' in config
        assert '"setup_path": "/settings"' in config
>       assert '"optional_service_unavailable"' in main
E       assert '"optional_service_unavailable"' in 'from __future__ import annotations\n\nimport json\nimport os\nimport secrets\nfrom datetime import datetime, timedelt...etadata),\n    )\n\n\ndef uuid_or_none(value: str | None) -> UUID | None:\n    return UUID(value) if value else None\n'

tests/test_config_validation.py:83: AssertionError
_______________________ test_onboarding_uses_glass_card ________________________

    def test_onboarding_uses_glass_card():
        text = read_page("OnboardingPage.vue")
>       assert "glass-card" in text, "OnboardingPage stepper must be in a glass-card"
E       AssertionError: OnboardingPage stepper must be in a glass-card
E       assert 'glass-card' in '<template>\n  <q-page class="column q-gutter-lg">\n    <NexusPageHero eyebrow="1-click operational setup" title="Onbo...tep = ref(1)\n</script>\n<style scoped>\n.nexus-stepper {\n  background: var(--nexus-panel) !important;\n}\n</style>\n'

tests/test_v1_productization.py:183: AssertionError
______________________ test_settings_page_has_validation _______________________

    def test_settings_page_has_validation():
        text = read_page("SettingsPage.vue")
>       assert ":rules" in text, "Settings must have input validation rules"
E       AssertionError: Settings must have input validation rules
E       assert ':rules' in '<template>\n  <q-page class="column q-gutter-lg">\n    <NexusPageHero eyebrow="Setup" title="Settings" subtitle="Vali...  failed.value = true\n    message.value = error instanceof Error ? error.message : String(error)\n  }\n}\n</script>\n'

tests/test_v1_productization.py:199: AssertionError
_________________________ test_settings_page_has_save __________________________

    def test_settings_page_has_save():
        text = read_page("SettingsPage.vue")
>       assert "localStorage" in text, "Settings must persist to localStorage"
E       AssertionError: Settings must persist to localStorage
E       assert 'localStorage' in '<template>\n  <q-page class="column q-gutter-lg">\n    <NexusPageHero eyebrow="Setup" title="Settings" subtitle="Vali...  failed.value = true\n    message.value = error instanceof Error ? error.message : String(error)\n  }\n}\n</script>\n'

tests/test_v1_productization.py:205: AssertionError
_________________ test_settings_page_has_service_health_check __________________

    def test_settings_page_has_service_health_check():
        text = read_page("SettingsPage.vue")
>       assert "serviceStatus" in text or "checkServices" in text
E       assert ('serviceStatus' in '<template>\n  <q-page class="column q-gutter-lg">\n    <NexusPageHero eyebrow="Setup" title="Settings" subtitle="Vali...  failed.value = true\n    message.value = error instanceof Error ? error.message : String(error)\n  }\n}\n</script>\n' or 'checkServices' in '<template>\n  <q-page class="column q-gutter-lg">\n    <NexusPageHero eyebrow="Setup" title="Settings" subtitle="Vali...  failed.value = true\n    message.value = error instanceof Error ? error.message : String(error)\n  }\n}\n</script>\n')

tests/test_v1_productization.py:211: AssertionError
=========================== short test summary info ============================
FAILED tests/test_config_validation.py::test_gateway_config_contract_is_actionable_and_redacted
FAILED tests/test_v1_productization.py::test_onboarding_uses_glass_card - Ass...
FAILED tests/test_v1_productization.py::test_settings_page_has_validation - A...
FAILED tests/test_v1_productization.py::test_settings_page_has_save - Asserti...
FAILED tests/test_v1_productization.py::test_settings_page_has_service_health_check
5 failed, 252 passed, 2 skipped in 1.34s
No obvious secrets detected by local regex scan.

> @personal-os/web@0.7.0 build /home/caion/Documentos/github/personal-os-scaffold/personal-os/apps/web
> quasar build


--------------------------------------------------------
 INCOMPATIBLE NODE VERSION
 @quasar/app-vite requires Node 22.22.0 or superior

 You are running Node v18.20.7
 Please install a compatible Node version and try again
--------------------------------------------------------

 ELIFECYCLE  Command failed with exit code 1.
```

Current known failure examples may include:
- missing structured error constant such as optional_service_unavailable
- page missing expected visual class such as glass-card
- Settings page missing validation rules
- Settings page missing localStorage persistence contract
- Settings page missing serviceStatus/checkServices contract

Repair requirements:
1. Inspect only relevant files.
2. Fix the actual root cause.
3. Add or preserve tests.
4. Run the failing command again if possible.
5. Run:
   - python3 -m pytest tests -q
   - ./scripts/check-secrets.sh
6. Write a report to:
   .agents/reports/auto-repair-pre-merge-20260608-072820/report.md

Report must include:
- root cause
- files changed
- tests run
- results
- remaining risks
