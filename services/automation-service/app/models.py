from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class NodeType(StrEnum):
    NOOP = "noop"
    TRANSFORM = "transform"
    EMIT_EVENT = "emit_event"
    HTTP_REQUEST = "http_request"
    MODULE_API = "module_api"
    COMMAND_REQUEST = "command_request"
    NOTIFICATION = "notification"
    N8N_WEBHOOK = "n8n_webhook"
    ARTIFACT = "artifact"
    APPROVAL_GATE = "approval_gate"


class TriggerType(StrEnum):
    MANUAL = "manual"
    EVENT = "event"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"


class RetryPolicy(BaseModel):
    max_attempts: int = Field(default=1, ge=1, le=8)
    backoff_seconds: float = Field(default=0.0, ge=0.0, le=3600.0)
    backoff_multiplier: float = Field(default=2.0, ge=1.0, le=10.0)


class WorkflowTrigger(BaseModel):
    type: TriggerType = TriggerType.MANUAL
    topic: str | None = None
    cron: str | None = None
    every_seconds: int | None = Field(default=None, ge=10, le=31_536_000)
    webhook_path: str | None = None
    enabled: bool = True

    @model_validator(mode="after")
    def validate_shape(self) -> "WorkflowTrigger":
        if self.type == TriggerType.EVENT and not self.topic:
            raise ValueError("event triggers require topic")
        if self.type == TriggerType.SCHEDULE and not (self.cron or self.every_seconds):
            raise ValueError("schedule triggers require cron or every_seconds")
        if self.type == TriggerType.WEBHOOK and not self.webhook_path:
            raise ValueError("webhook triggers require webhook_path")
        return self


class WorkflowNode(BaseModel):
    id: str = Field(min_length=1, max_length=96, pattern=r"^[a-zA-Z0-9_.:-]+$")
    type: NodeType = NodeType.NOOP
    name: str | None = Field(default=None, max_length=180)
    config: dict[str, Any] = Field(default_factory=dict)
    scopes: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    retry: RetryPolicy = Field(default_factory=RetryPolicy)
    timeout_seconds: int = Field(default=30, ge=1, le=300)

    @field_validator("scopes")
    @classmethod
    def normalize_scopes(cls, value: list[str]) -> list[str]:
        return sorted(set(v.strip() for v in value if v.strip()))


class WorkflowEdge(BaseModel):
    from_node: str = Field(alias="from", min_length=1, max_length=96)
    to_node: str = Field(alias="to", min_length=1, max_length=96)


class WorkflowSpec(BaseModel):
    version: str = Field(default="1", max_length=32)
    name: str = Field(min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    triggers: list[WorkflowTrigger] = Field(default_factory=lambda: [WorkflowTrigger(type=TriggerType.MANUAL)])
    nodes: list[WorkflowNode] = Field(min_length=1, max_length=64)
    edges: list[WorkflowEdge] = Field(default_factory=list, max_length=256)
    max_concurrency: int = Field(default=1, ge=1, le=16)
    requires_approval: bool = False
    labels: dict[str, str] = Field(default_factory=dict)

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 32:
            raise ValueError("labels may not exceed 32 entries")
        return {str(k)[:80]: str(v)[:240] for k, v in value.items()}

    @property
    def node_ids(self) -> set[str]:
        return {node.id for node in self.nodes}

    def node_by_id(self, node_id: str) -> WorkflowNode:
        for node in self.nodes:
            if node.id == node_id:
                return node
        raise KeyError(node_id)


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PENDING_APPROVAL = "pending_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PENDING_APPROVAL = "pending_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
