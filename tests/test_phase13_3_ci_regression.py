from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_local_github_logs_are_not_packaged_or_tracked_candidates():
    assert not (ROOT / 'latest_commit_logs.txt').exists()
    assert not (ROOT / 'gh-logs.sh').exists()
    gitignore = (ROOT / '.gitignore').read_text()
    assert 'latest_commit_logs.txt' in gitignore
    assert 'gh-logs.sh' in gitignore


def test_quasar_table_pages_use_typed_columns():
    for rel in [
        'apps/web/src/pages/GeospatialPage.vue',
        'apps/web/src/pages/OfflineQueuePage.vue',
        'apps/web/src/pages/StudyPage.vue',
    ]:
        text = (ROOT / rel).read_text()
        assert "import type { QTableColumn } from 'quasar'" in text, rel
        assert 'const columns: QTableColumn[] = [' in text, rel


def test_api_upload_test_uses_safe_tuple_cast_for_typescript():
    text = (ROOT / 'apps/web/src/services/api.test.ts').read_text()
    assert 'as unknown as Array<[RequestInfo | URL, RequestInit | undefined]>' in text
    assert 'const init = calls[0]?.[1]' in text
