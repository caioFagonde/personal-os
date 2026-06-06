import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.conflict import compare_clock, decide_merge, merge_field, merge_set_union

def test_compare_clock_relations():
    assert compare_clock({'a': 1}, {'a': 2}) == 'before'
    assert compare_clock({'a': 2}, {'a': 1}) == 'after'
    assert compare_clock({'a': 2}, {'a': 2}) == 'equal'
    assert compare_clock({'a': 2}, {'b': 2}) == 'concurrent'

def test_field_merge_detects_conflict():
    merged, conflicts = merge_field({'title': 'A', 'body': 'x'}, {'title': 'B', 'body': 'y'}, {'title'}, {'title', 'body'})
    assert merged['body'] == 'y'
    assert conflicts == ['title']

def test_set_union_is_stable_ordered():
    assert merge_set_union(['a', 'b'], ['b', 'c']) == ['a', 'b', 'c']

def test_manual_concurrent_requires_approval():
    decision = decide_merge({'phone': 1}, {'pc': 1}, 'manual')
    assert decision.needs_manual_resolution is True
