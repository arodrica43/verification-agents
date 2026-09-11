"""Shared enumerations used across schemas."""

from __future__ import annotations

from enum import StrEnum


class ArtifactLifecycle(StrEnum):
    DRAFT = "draft"
    RESEARCHED = "researched"
    REVIEWED = "reviewed"
    FORMALIZED = "formalized"
    PROVEN = "proven"
    VERIFIED = "verified"
    CERTIFIED = "certified"
    DEPRECATED = "deprecated"
    INVALIDATED = "invalidated"


class Confidentiality(StrEnum):
    PUBLIC = "public"
    ORGANIZATION = "organization"
    WORKSPACE = "workspace"
    PROJECT = "project"
    PRIVATE = "private"
    SECRET = "secret"


class CreatorType(StrEnum):
    USER = "user"
    AGENT = "agent"
    SERVICE = "service"
    SYSTEM = "system"


class TrustLevel(StrEnum):
    UNTRUSTED = "untrusted"
    RESEARCH = "research"
    HUMAN_REVIEWED = "human_reviewed"
    FORMALIZED = "formalized"
    KERNEL_VERIFIED = "kernel_verified"
    CERTIFIED = "certified"


class ProvenanceRelation(StrEnum):
    DERIVED_FROM = "derived_from"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    REFINES = "refines"
    FORMALIZES = "formalizes"
    ASSUMES = "assumes"
    DEPENDS_ON = "depends_on"
    PROVEN_BY = "proven_by"
    VERIFIED_BY = "verified_by"
    GENERATED_BY = "generated_by"
    REVIEWED_BY = "reviewed_by"
    SUPERSEDES = "supersedes"
    VALIDATES = "validates"
    INVALIDATES = "invalidates"
    EXTRACTED_FROM = "extracted_from"
    CITES = "cites"
    IMPORTS = "imports"
    INSTANTIATED_FROM = "instantiated_from"
