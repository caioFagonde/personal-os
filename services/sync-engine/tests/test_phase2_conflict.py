import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.conflict import merge_crdt_text, resolve_payload


def test_crdt_text_deduplicates_and_orders_ops():
    local = {"text": "", "ops": [{"id": "b:1", "type": "append", "value": "world"}]}
    remote = {"text": "", "ops": [{"id": "a:1", "type": "append", "value": "hello "}, {"id": "b:1", "type": "append", "value": "world"}]}
    merged = merge_crdt_text(local, remote)
    assert merged["text"] == "hello world"
    assert len(merged["ops"]) == 2


def test_field_merge_concurrent_conflict_requires_manual_surface():
    result = resolve_payload(
        {"title": "local", "body": "same"},
        {"title": "remote", "body": "same"},
        {"phone": 1},
        {"pc": 1},
        "field_merge",
        {"title"},
        {"title"},
    )
    assert result.needs_manual_resolution is True
    assert result.conflicts == ["title"]


def test_set_union_merges_tags_without_manual_conflict():
    result = resolve_payload(
        {"tags": ["math", "physics"]},
        {"tags": ["physics", "programming"]},
        {"phone": 1},
        {"pc": 1},
        "set_union",
    )
    assert result.needs_manual_resolution is False
    assert result.payload["tags"] == ["math", "physics", "programming"]
