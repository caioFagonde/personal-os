from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

ENTITY_TYPES: dict[str, dict[str, Any]] = {
    "person": {"sensitive": True, "required": ["name"], "domains": ["social", "identity"]},
    "goal": {"sensitive": False, "required": ["title"], "domains": ["growth", "planning"]},
    "habit": {"sensitive": False, "required": ["title"], "domains": ["behavior", "health"]},
    "project": {"sensitive": False, "required": ["title"], "domains": ["work", "creation"]},
    "note": {"sensitive": False, "required": ["title"], "domains": ["knowledge"]},
    "location": {"sensitive": True, "required": ["name"], "domains": ["geospatial"]},
    "health_metric": {"sensitive": True, "required": ["metric", "value"], "domains": ["health"]},
    "study_item": {"sensitive": False, "required": ["title"], "domains": ["learning"]},
    "workflow": {"sensitive": False, "required": ["name"], "domains": ["automation"]},
}

RELATION_TYPES: dict[str, dict[str, str]] = {
    "supports": {"from": "*", "to": "goal"},
    "blocks": {"from": "*", "to": "goal"},
    "part_of": {"from": "*", "to": "*"},
    "depends_on": {"from": "*", "to": "*"},
    "practiced_by": {"from": "habit", "to": "person"},
    "located_at": {"from": "*", "to": "location"},
    "derived_from": {"from": "*", "to": "note"},
    "triggers": {"from": "workflow", "to": "*"},
}

DOMAIN_BY_EVENT_PREFIX = {
    "study.": "learning",
    "zettel.": "knowledge",
    "note.": "knowledge",
    "fitness.": "health",
    "nutrition.": "health",
    "mindfulness.": "mindfulness",
    "geo.": "geospatial",
    "geospatial.": "geospatial",
    "automation.": "automation",
    "research.": "research",
    "command.": "operations",
}

@dataclass(frozen=True)
class EntityFingerprint:
    entity_type: str
    natural_key: str
    fingerprint: str


def ontology_snapshot() -> dict[str, Any]:
    return {"entity_types": ENTITY_TYPES, "relationship_types": RELATION_TYPES, "event_prefix_domains": DOMAIN_BY_EVENT_PREFIX}


def validate_entity(entity_type: str, properties: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    spec = ENTITY_TYPES.get(entity_type)
    if not spec:
        return [f"unknown entity type: {entity_type}"]
    for key in spec.get("required", []):
        if properties.get(key) in (None, ""):
            errors.append(f"missing required property: {key}")
    return errors


def validate_relationship(relation_type: str, from_type: str, to_type: str) -> list[str]:
    spec = RELATION_TYPES.get(relation_type)
    if not spec:
        return [f"unknown relationship type: {relation_type}"]
    errors: list[str] = []
    if spec["from"] != "*" and spec["from"] != from_type:
        errors.append(f"relationship {relation_type} expects from={spec['from']}, got {from_type}")
    if spec["to"] != "*" and spec["to"] != to_type:
        errors.append(f"relationship {relation_type} expects to={spec['to']}, got {to_type}")
    return errors


def infer_domains(event_type: str, payload: dict[str, Any] | None = None) -> list[str]:
    payload = payload or {}
    domains: set[str] = set()
    for prefix, domain in DOMAIN_BY_EVENT_PREFIX.items():
        if event_type.startswith(prefix):
            domains.add(domain)
    explicit = payload.get("domain") or payload.get("domains")
    if isinstance(explicit, str):
        domains.add(explicit)
    elif isinstance(explicit, list):
        domains.update(str(item) for item in explicit if item)
    if not domains:
        domains.add("general")
    return sorted(domains)


def stable_fingerprint(entity_type: str, properties: dict[str, Any]) -> EntityFingerprint:
    natural = str(properties.get("id") or properties.get("slug") or properties.get("title") or properties.get("name") or properties)
    normalized = " ".join(natural.lower().strip().split())
    digest = sha256(f"{entity_type}:{normalized}".encode()).hexdigest()[:32]
    return EntityFingerprint(entity_type=entity_type, natural_key=normalized, fingerprint=digest)
