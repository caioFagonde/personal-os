from app.ontology import infer_domains, stable_fingerprint, validate_entity, validate_relationship


def test_validate_entity_required_fields():
    assert validate_entity("goal", {}) == ["missing required property: title"]
    assert validate_entity("goal", {"title": "Build Phase 8"}) == []
    assert validate_entity("unknown", {}) == ["unknown entity type: unknown"]


def test_validate_relationship_contracts():
    assert validate_relationship("supports", "habit", "goal") == []
    errors = validate_relationship("supports", "habit", "project")
    assert "expects to=goal" in errors[0]


def test_infer_domains_from_prefix_and_payload():
    assert infer_domains("study.session.completed", {}) == ["learning"]
    assert infer_domains("custom.event", {"domains": ["health", "learning"]}) == ["health", "learning"]
    assert infer_domains("unknown.event", {}) == ["general"]


def test_stable_fingerprint_is_normalized():
    a = stable_fingerprint("goal", {"title": "  Master   Lie Theory "})
    b = stable_fingerprint("goal", {"title": "master lie theory"})
    assert a.fingerprint == b.fingerprint
    assert a.natural_key == "master lie theory"


def test_snapshot_and_string_domain_and_from_type_error():
    snap = __import__('app.ontology', fromlist=['ontology_snapshot']).ontology_snapshot()
    assert 'goal' in snap['entity_types']
    assert validate_relationship('unknown_rel', 'goal', 'goal') == ['unknown relationship type: unknown_rel']
    assert validate_relationship('practiced_by', 'goal', 'person')[0].startswith('relationship practiced_by expects from=habit')
    assert infer_domains('custom.event', {'domain': 'custom'}) == ['custom']
