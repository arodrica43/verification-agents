"""Versioned ProblemSpec schema."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SystemEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str = ""
    kind: str | None = None


class SystemVariable(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str = ""
    domain: str | None = None
    units: str | None = None


class SystemParameter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str = ""
    value: str | None = None
    units: str | None = None


class SystemRelation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str = ""
    participants: list[str] = Field(default_factory=list)


class SystemInterface(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str = ""


class SystemEnvironment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str = ""


class SystemModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entities: list[SystemEntity] = Field(default_factory=list)
    variables: list[SystemVariable] = Field(default_factory=list)
    parameters: list[SystemParameter] = Field(default_factory=list)
    relations: list[SystemRelation] = Field(default_factory=list)
    interfaces: list[SystemInterface] = Field(default_factory=list)
    environment: list[SystemEnvironment] = Field(default_factory=list)


class GoalItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    statement: str
    priority: str | None = None


class ClaimItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    statement: str
    informal: bool = True


class AssumptionRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    statement: str
    category: str | None = None


class UncertaintyItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    description: str


class OpenQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    question: str


class ProblemScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    notes: str = ""


class ValidityCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    expression: str
    description: str = ""


class ProblemSpec(BaseModel):
    """Structured representation of a user's problem (schema_version 1.0)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0"
    title: str
    description: str
    system: SystemModel = Field(default_factory=SystemModel)
    goals: list[GoalItem] = Field(default_factory=list)
    claims: list[ClaimItem] = Field(default_factory=list)
    assumptions: list[AssumptionRef] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    uncertainties: list[UncertaintyItem] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    scope: ProblemScope = Field(default_factory=ProblemScope)
    validity_conditions: list[ValidityCondition] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
