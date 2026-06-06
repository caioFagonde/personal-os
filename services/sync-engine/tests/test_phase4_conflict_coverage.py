from datetime import datetime, timezone

from app.conflict import merge_lww, merge_clocks, merge_crdt_text, resolve_payload


def test_merge_clocks_and_lww_dates():
    assert merge_clocks({'a': 1}, {'a': 2, 'b': 1}) == {'a': 2, 'b': 1}
    assert merge_lww({'v': 'old'}, {'v': 'new'}, datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2024, 1, 2, tzinfo=timezone.utc)) == {'v': 'new'}
    assert merge_lww({'v': 'old'}, {'v': 'new'}, '2024-01-03', '2024-01-02') == {'v': 'old'}


def test_crdt_text_set_and_plain_text_fallback():
    local = {'text': 'local', 'ops': [{'id': 'b:1', 'type': 'append', 'value': ' world'}]}
    remote = {'text': 'remote', 'ops': [{'id': 'a:1', 'type': 'set', 'value': 'hello'}]}
    assert merge_crdt_text(local, remote)['text'] == 'hello world'
    assert merge_crdt_text({'text': 'local'}, {'text': 'remote'})['text'] == 'remote'


def test_resolve_before_equal_after_and_lww():
    before = resolve_payload({'v': 1}, {'v': 2}, {'a': 1}, {'a': 2}, 'field_merge')
    assert before.payload == {'v': 2}
    equal = resolve_payload({'v': 1}, {'v': 2}, {'a': 2}, {'a': 2}, 'field_merge')
    assert equal.relation == 'equal' and equal.payload == {'v': 2}
    after = resolve_payload({'v': 1}, {'v': 2}, {'a': 3}, {'a': 2}, 'field_merge')
    assert after.payload == {'v': 1}
    lww = resolve_payload({'v': 1}, {'v': 2}, {'a': 1}, {'b': 1}, 'lww')
    assert lww.payload == {'v': 2}


def test_counter_crdt_and_unknown_strategy():
    counter = resolve_payload({'count': 2, 'label': 'local'}, {'count': 3, 'label': 'remote'}, {'a': 1}, {'b': 1}, 'counter')
    assert counter.payload == {'count': 5, 'label': 'remote'}
    crdt = resolve_payload({'ops': []}, {'ops': [{'id': 'a:1', 'type': 'append', 'value': 'x'}]}, {'a': 1}, {'b': 1}, 'crdt_text')
    assert crdt.payload['text'] == 'x'
    unknown = resolve_payload({'v': 1}, {'v': 2}, {'a': 1}, {'b': 1}, 'bespoke')
    assert unknown.needs_manual_resolution is True
    assert unknown.conflicts == ['__unknown_strategy__']


def test_set_union_non_list_overwrite_branch():
    result = resolve_payload({'tags': ['a'], 'status': 'old'}, {'tags': ['b'], 'status': 'new'}, {'a': 1}, {'b': 1}, 'set_union')
    assert result.payload['tags'] == ['a', 'b']
    assert result.payload['status'] == 'new'
