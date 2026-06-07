from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase_4_settings_string_values_are_valid_jsonb():
    migration = ROOT / 'infra/postgres/migrations/003_phase_4.sql'
    text = migration.read_text()
    assert "'io.personalos.mobile'::jsonb" not in text
    assert "'io.personalos.desktop'::jsonb" not in text
    assert "to_jsonb('io.personalos.mobile'::text)" in text
    assert "to_jsonb('io.personalos.desktop'::text)" in text


def test_no_bare_dotted_strings_cast_to_jsonb_in_migrations():
    for migration in (ROOT / 'infra/postgres/migrations').glob('*.sql'):
        text = migration.read_text()
        assert "'io." not in text or "'io." not in text.replace("to_jsonb('io.", "")
