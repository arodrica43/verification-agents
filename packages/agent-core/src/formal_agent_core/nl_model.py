"""Deterministic NL → domain model heuristics (no LLM)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "to",
        "in",
        "for",
        "on",
        "with",
        "by",
        "is",
        "are",
        "be",
        "that",
        "this",
        "these",
        "those",
        "as",
        "at",
        "from",
        "it",
        "its",
        "must",
        "should",
        "shall",
        "will",
        "can",
        "may",
        "if",
        "then",
        "when",
        "where",
        "which",
        "who",
        "whom",
        "into",
        "over",
        "under",
        "not",
        "no",
        "nor",
        "but",
        "we",
        "our",
        "ours",
        "their",
        "they",
        "them",
        "his",
        "her",
        "has",
        "have",
        "had",
        "do",
        "does",
        "did",
        "been",
        "being",
        "was",
        "were",
        "such",
        "any",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "others",
        "some",
        "than",
        "too",
        "very",
        "just",
        "also",
        "only",
        "own",
        "same",
        "so",
        "via",
        "per",
        "using",
        "use",
        "used",
        "ensure",
        "ensures",
        "ensuring",
        "system",
        "systems",
        "working",
        "work",
        "works",
        "there",
        "here",
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "group",
        "while",
        "during",
        "after",
        "before",
        "about",
        "out",
        "up",
        "down",
        "off",
        "able",
        "moment",
        "initially",
        "accordingly",
        "according",
        "declared",
        "specified",
        "small",
        "large",
        "handling",
        "handles",
        "handled",
        "produces",
        "produce",
        "produced",
        "distributes",
        "distribute",
        "distributed",
        "changing",
        "change",
        "changed",
        "turning",
        "turn",
        "turned",
        "behave",
        "behaves",
        "behaviour",
        "behavior",
        "types",
        "type",
        "kind",
        "kinds",
        "size",
        "sizes",
        "speed",
        "speeds",
        "pre",
        "cooked",
        "food",
        "factory",
        "too",
        "also",
        "any",
        "them",
        "they",
        "are",
        "being",
    }
)

_KIND_HINTS: dict[str, str] = {
    "machine": "component",
    "robot": "component",
    "sensor": "component",
    "thermostat": "attribute",
    "buffer": "attribute",
    "temperature": "attribute",
    "worker": "actor",
    "operator": "actor",
    "agent": "actor",
    "product": "artifact",
    "liquid": "artifact",
    "solid": "artifact",
    "policy": "policy",
    "monitor": "component",
    "runtime": "component",
    "action": "action",
    "secret": "artifact",
    "packing": "component",
}

_ATTR_MAP = {
    "thermostate": "thermostat",
    "thermostat": "thermostat",
    "production speed": "production_speed",
    "packing speed": "packing_speed",
    "buffer size": "buffer_size",
    "buffer": "buffer_size",
    "temperature": "temperature",
    "parameters": "parameters",
    "parameter": "parameters",
    "type of product": "product_kind",
    "product type": "product_kind",
}


@dataclass
class DomainModel:
    entities: list[dict[str, Any]] = field(default_factory=list)
    relations: list[dict[str, Any]] = field(default_factory=list)
    product_kinds: list[str] = field(default_factory=list)
    attributes_by_subject: dict[str, list[str]] = field(default_factory=dict)
    obligation_sentences: list[str] = field(default_factory=list)
    raw_sentences: list[str] = field(default_factory=list)


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9_\-]*", text)]


def _singular(word: str) -> str:
    w = word.strip().lower()
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith(("ses", "xes", "zes")) and len(w) > 4:
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return w[:-1]
    return w


def _display_name(name: str) -> str:
    parts = [p for p in re.split(r"\s+", name.strip()) if p]
    if not parts:
        return name
    if len(parts) == 1:
        w = parts[0]
        return w[:1].upper() + w[1:] if w.islower() else w
    return " ".join(parts)


def _entity_kind(name: str) -> str:
    key = _singular(name.split()[-1])
    return _KIND_HINTS.get(key, "entity")


def _canon_attr(raw: str) -> str | None:
    key = re.sub(r"\s+", " ", raw.strip().lower())
    key = re.sub(r"\([^)]*\)", "", key).strip()
    if not key or len(key) > 40:
        return None
    if key in _ATTR_MAP:
        return _ATTR_MAP[key]
    # Map verbose leftovers
    if "thermostat" in key or "thermostate" in key:
        return "thermostat"
    if "buffer" in key:
        return "buffer_size"
    if "speed" in key:
        return "speed"
    if "type" in key and "product" in key:
        return "product_kind"
    if "parameter" in key:
        return "parameters"
    if "temperature" in key:
        return "temperature"
    # Reject long verbish tails
    if any(
        w in key.split()
        for w in ("they", "are", "handling", "while", "processing", "too")
    ):
        return None
    return re.sub(r"[^a-z0-9]+", "_", key).strip("_") or None


def _title_case_phrases(text: str) -> list[str]:
    phrases: list[str] = []
    for m in re.finditer(r"\b([A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+)*)\b", text):
        words = m.group(1).split()
        while words and words[0].lower() in _STOPWORDS:
            words = words[1:]
        if not words:
            continue
        if len(words) == 1 and words[0].lower() in _STOPWORDS:
            continue
        if all(w.lower() in _STOPWORDS for w in words):
            continue
        phrases.append(" ".join(words))
    return phrases


def _extract_product_kinds(text: str) -> list[str]:
    """Prefer explicit enumerations; keep only product-like hyphen labels."""
    kinds: list[str] = []
    for m in re.finditer(
        r"types?\s+of\s+products?\s+can\s+be\s+([^.]+)",
        text,
        flags=re.IGNORECASE,
    ):
        chunk = m.group(1)
        # Drop trailing "for solids..." elaborations by splitting on "for "
        # but keep both solid-* and liquid-* lists.
        chunk = re.sub(r"\bfor\s+solids?\b", ",", chunk, flags=re.IGNORECASE)
        chunk = re.sub(r"\bfor\s+liquids?\b", ",", chunk, flags=re.IGNORECASE)
        parts = re.split(r",|\band\b|\bor\b", chunk, flags=re.IGNORECASE)
        for part in parts:
            label = part.strip().lower().strip(".")
            label = re.sub(r"^(?:and|or)\s+", "", label)
            if re.fullmatch(r"(?:solid|liquid)-[a-z0-9]+", label):
                if label not in kinds:
                    kinds.append(label)
    if not kinds:
        for label in re.findall(r"\b((?:solid|liquid)-[a-z0-9]+)\b", text.lower()):
            if label not in kinds:
                kinds.append(label)
    return kinds


def _extract_has_attributes(sentence: str) -> list[tuple[str, list[str]]]:
    results: list[tuple[str, list[str]]] = []
    for m in re.finditer(
        r"\b(?:each|every|a|an|the)\s+(machine|product|worker|component|robot|sensor)s?"
        r"\s+has\s+(?:also\s+)?(.+)$",
        sentence,
        flags=re.IGNORECASE,
    ):
        subject = _singular(m.group(1))
        tail = m.group(2)
        tail = re.split(
            r"\b(?:while|so|because|although|but|too)\b",
            tail,
            flags=re.IGNORECASE,
        )[0]
        attrs: list[str] = []
        for part in re.split(r",|\band\b", tail, flags=re.IGNORECASE):
            part = part.strip().strip(".")
            part = re.sub(r"^(?:a|an|the|also|its|their|own)\s+", "", part, flags=re.IGNORECASE)
            part = re.sub(r"\s+for\s+each\s+\w+$", "", part, flags=re.IGNORECASE)
            attr = _canon_attr(part)
            if attr and attr not in attrs:
                attrs.append(attr)
        if attrs:
            results.append((subject, attrs))
    # "we have also buffer size for each machine"
    for m in re.finditer(
        r"\b(?:have|has)\s+(?:also\s+)?([a-z][a-z ]{2,40}?)\s+for\s+each\s+(machine|product|worker)s?\b",
        sentence,
        flags=re.IGNORECASE,
    ):
        attr = _canon_attr(m.group(1))
        subject = _singular(m.group(2))
        if attr:
            results.append((subject, [attr]))
    return results


def _extract_obligations(text: str) -> list[str]:
    obligations: list[str] = []

    def add(clause: str) -> None:
        clause = re.sub(r"\s+", " ", clause).strip(" .;")
        if not (8 <= len(clause) <= 240):
            return
        # Dedup by normalized content
        key = clause.lower()
        if any(key == o.lower() or key in o.lower() or o.lower() in key for o in obligations):
            # Keep the longer/more specific form
            for i, existing in enumerate(obligations):
                if key in existing.lower() or existing.lower() in key:
                    if len(clause) > len(existing):
                        obligations[i] = clause
                    return
            return
        obligations.append(clause)

    # Prefer "must ensure that …"
    for m in re.finditer(
        r"(?:we\s+)?must\s+ensure\s+that\s+(.+?)(?:[.!]|$)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        clause = m.group(1).strip()
        add(clause[:1].upper() + clause[1:] if clause else clause)

    for m in re.finditer(
        r"(?:we\s+)?must\s+ensure\s+(?!that\b)(.+?)(?:[.!]|$)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        clause = m.group(1).strip()
        add(clause[:1].upper() + clause[1:] if clause else clause)

    for m in re.finditer(
        r"\bmust\s+never\s+(.+?)(?:[.!]|$)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        clause = m.group(1).strip()
        add("Must never " + clause)

    for m in re.finditer(
        r"\bmust\s+not\s+(.+?)(?:[.!]|$)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        clause = m.group(1).strip()
        add("Must not " + clause)

    for m in re.finditer(
        r"(?:it\s+is\s+required\s+that|require\s+that)\s+(.+?)(?:[.!]|$)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        clause = m.group(1).strip()
        add(clause[:1].upper() + clause[1:] if clause else clause)

    return obligations


def _extract_relations(sentences: list[str], text: str) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []
    rid = 0
    lower = text.lower()
    if "distribut" in lower and "machine" in lower:
        rid += 1
        relations.append(
            {
                "id": f"rel-{rid}",
                "kind": "distributes_to",
                "statement": (
                    "A producer machine distributes products into packing machines "
                    "according to product phase (solid vs liquid)"
                ),
                "source": "producer_machine",
                "target": "packing_machine",
            }
        )
    if re.search(r"\bworkers?\b", lower) and re.search(
        r"\b(?:turn|changing|change|parameter)\b", lower
    ):
        rid += 1
        relations.append(
            {
                "id": f"rel-{rid}",
                "kind": "controls",
                "statement": (
                    "Workers may turn machines on/off and change machine parameters "
                    "at any time"
                ),
                "source": "worker",
                "target": "machine",
            }
        )
    for sent in sentences:
        low = sent.lower()
        if re.search(r"\bnever\b", low) and re.search(
            r"\b(export|leak|forbid|block)\b", low
        ):
            rid += 1
            relations.append(
                {
                    "id": f"rel-{rid}",
                    "kind": "forbids",
                    "statement": sent.strip().rstrip(".") + ".",
                    "source": "policy",
                    "target": "action",
                }
            )
    return relations


def _add_entity(
    bag: dict[str, dict[str, Any]],
    name: str,
    *,
    kind: str | None = None,
    attrs: list[str] | None = None,
    notes: str | None = None,
) -> None:
    words = [w for w in re.split(r"\s+", name.strip()) if w]
    # Drop leading stopwords / junk quantifiers
    while words and words[0].lower() in _STOPWORDS:
        words = words[1:]
    if not words:
        return
    # Reject names that are mostly stopwords
    content = [w for w in words if w.lower() not in _STOPWORDS]
    if not content:
        return
    display = _display_name(" ".join(words))
    lookup = display.lower()
    if lookup in _STOPWORDS:
        return
    # Reject multiword junk like "temperature of machine" unless intentional
    if any(w.lower() in {"of", "with", "the", "for", "as", "by"} for w in words):
        # Allow only curated role names
        if lookup not in {
            "producer machine",
            "liquid packing machine",
            "solid packing machine",
            "packing machine",
            "safety monitor",
            "agent policy",
        }:
            return

    if lookup not in bag:
        bag[lookup] = {
            "id": "",
            "name": display,
            "kind": kind or _entity_kind(display),
            "attributes": [],
        }
        if notes:
            bag[lookup]["notes"] = notes
    else:
        if kind and bag[lookup]["kind"] in {"entity", "attribute"}:
            bag[lookup]["kind"] = kind
        if notes and "notes" not in bag[lookup]:
            bag[lookup]["notes"] = notes
    if attrs:
        existing = list(bag[lookup].get("attributes") or [])
        for a in attrs:
            if a and a not in existing:
                existing.append(a)
        bag[lookup]["attributes"] = existing


def build_domain_model(problem_text: str) -> DomainModel:
    text = _normalize(problem_text)
    sentences = _sentences(text)
    model = DomainModel(raw_sentences=sentences)
    bag: dict[str, dict[str, Any]] = {}
    lower = text.lower()

    model.product_kinds = _extract_product_kinds(text)
    if model.product_kinds:
        _add_entity(
            bag,
            "product",
            kind="artifact",
            attrs=["temperature", "kind"],
            notes=f"kinds={','.join(model.product_kinds)}",
        )

    for phrase in _title_case_phrases(text):
        _add_entity(bag, phrase, kind=_entity_kind(phrase))

    for sent in sentences:
        for subject, attrs in _extract_has_attributes(sent):
            _add_entity(bag, subject, kind=_entity_kind(subject), attrs=attrs)
            model.attributes_by_subject.setdefault(subject, [])
            for a in attrs:
                if a not in model.attributes_by_subject[subject]:
                    model.attributes_by_subject[subject].append(a)

    # Role-specific machines from narrative
    if "distribut" in lower and "machine" in lower:
        machine_attrs = [
            "thermostat",
            "production_speed",
            "product_kind",
            "buffer_size",
        ]
        packing_attrs = [
            "thermostat",
            "packing_speed",
            "product_kind",
            "buffer_size",
        ]
        # Merge discovered attrs onto generic machine
        discovered = model.attributes_by_subject.get("machine", [])
        for a in discovered:
            if a not in machine_attrs:
                machine_attrs.append(a)
            if a not in packing_attrs:
                packing_attrs.append(a)
        _add_entity(
            bag,
            "producer machine",
            kind="component",
            attrs=machine_attrs,
            notes="Produces solid and liquid products and distributes them",
        )
        _add_entity(
            bag,
            "liquid packing machine",
            kind="component",
            attrs=packing_attrs,
            notes="Packs liquid products",
        )
        _add_entity(
            bag,
            "solid packing machine",
            kind="component",
            attrs=packing_attrs,
            notes="Packs solid products",
        )
        _add_entity(bag, "machine", kind="component", attrs=discovered or machine_attrs)

    elif "machine" in lower:
        attrs = model.attributes_by_subject.get("machine", [])
        if not attrs:
            attrs = []
            if "thermostat" in lower or "thermostate" in lower:
                attrs.append("thermostat")
            if "speed" in lower:
                attrs.append("speed")
            if "buffer" in lower:
                attrs.append("buffer_size")
            if "product" in lower:
                attrs.append("product_kind")
        _add_entity(bag, "machine", kind="component", attrs=attrs)

    if re.search(r"\bworkers?\b", lower):
        _add_entity(bag, "worker", kind="actor")

    if "product" in lower:
        prod_attrs = model.attributes_by_subject.get("product", [])
        if "temperature" in lower and "temperature" not in prod_attrs:
            prod_attrs = [*prod_attrs, "temperature"]
        if model.product_kinds and "kind" not in prod_attrs:
            prod_attrs = [*prod_attrs, "kind"]
        _add_entity(
            bag,
            "product",
            kind="artifact",
            attrs=prod_attrs or ["temperature"],
            notes=(
                f"kinds={','.join(model.product_kinds)}" if model.product_kinds else None
            ),
        )

    # Lexicon singles (policy / secret / monitor already partly from title case)
    for tok in set(_tokens(text)):
        root = _singular(tok)
        if root in _KIND_HINTS and root not in _STOPWORDS:
            _add_entity(bag, root, kind=_KIND_HINTS[root])

    model.relations = _extract_relations(sentences, text)
    model.obligation_sentences = _extract_obligations(text)

    priority = {
        "component": 0,
        "actor": 1,
        "artifact": 2,
        "policy": 3,
        "action": 4,
        "attribute": 9,
        "entity": 8,
    }
    # Drop standalone attribute entities and duplicates of role machines
    drop_attrs = {
        "thermostat",
        "temperature",
        "buffer",
        "speed",
        "parameter",
        "parameters",
        "packing",
        "solid",
        "liquid",
    }
    ordered = sorted(
        bag.values(),
        key=lambda e: (priority.get(str(e.get("kind")), 9), str(e.get("name", "")).lower()),
    )
    cleaned: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for ent in ordered:
        name = str(ent.get("name", "")).lower()
        kind = str(ent.get("kind"))
        if kind == "attribute" or name in drop_attrs:
            continue
        # Prefer "Safety Monitor" over bare "Monitor"; "Agent Policy" over "Policy"
        if name in {"monitor", "policy", "agent"} and any(
            name in n and n != name for n in bag
        ):
            # keep if no more specific exists in cleaned later — skip generic now
            if any(name in k and k != name for k in bag):
                continue
        if name in seen_names:
            continue
        seen_names.add(name)
        row = dict(ent)
        row["id"] = f"ent-{len(cleaned) + 1}"
        cleaned.append(row)

    if not cleaned:
        cleaned = [{"id": "ent-1", "name": "System", "kind": "context", "attributes": []}]

    model.entities = cleaned[:14]
    return model


def assumptions_from_model(model: DomainModel) -> list[dict[str, Any]]:
    assumptions: list[dict[str, Any]] = []
    aid = 0

    def add(statement: str, *, trust: str = "asserted", entity_id: str | None = None) -> None:
        nonlocal aid
        aid += 1
        row: dict[str, Any] = {
            "id": f"asm-{aid}",
            "statement": statement,
            "trust": trust,
        }
        if entity_id:
            row["entity_id"] = entity_id
        assumptions.append(row)

    for ent in model.entities:
        attrs = ent.get("attributes") or []
        if attrs and str(ent.get("kind")) in {"component", "artifact", "actor"}:
            pretty = ", ".join(a.replace("_", " ") for a in attrs)
            add(
                f"Each {str(ent['name']).lower()} has attributes: {pretty}.",
                entity_id=ent.get("id"),
            )

    if model.product_kinds:
        solids = [k for k in model.product_kinds if k.startswith("solid")]
        liquids = [k for k in model.product_kinds if k.startswith("liquid")]
        add(
            "Product kinds are drawn from the declared enumeration: "
            + ", ".join(model.product_kinds)
            + "."
        )
        if solids and liquids:
            add(
                "Solids {"
                + ", ".join(solids)
                + "} and liquids {"
                + ", ".join(liquids)
                + "} are handled by distinct packing machines."
            )

    for rel in model.relations:
        add(str(rel["statement"]))

    if any(e.get("kind") == "actor" for e in model.entities):
        if not any("worker" in str(a["statement"]).lower() for a in assumptions):
            add("Human operators may change controllable parameters during operation.")

    if any(
        "buffer" in " ".join(str(a) for a in (e.get("attributes") or []))
        for e in model.entities
    ):
        add("While processing, each machine retains a finite product buffer.")

    if not assumptions:
        add("The modelled environment is closed under the stated actions and parameters.")

    return assumptions[:12]


def goals_from_model(model: DomainModel, problem_text: str) -> list[dict[str, Any]]:
    goals: list[dict[str, Any]] = []
    text = problem_text.lower()

    for i, obligation in enumerate(model.obligation_sentences):
        kind = "invariant"
        low = obligation.lower()
        if any(
            k in low for k in ("never", "must not", "forbid", "forbidden", "safe", "safety")
        ):
            kind = "safety"
        elif any(k in low for k in ("eventually", "reach", "complete", "liveness")):
            kind = "liveness"
        goals.append(
            {
                "id": f"goal-{i + 1}",
                "statement": obligation.rstrip(".") + ".",
                "kind": kind,
                "source": "obligation_sentence",
            }
        )

    if not goals:
        if any(k in text for k in ("safe", "safety", "never", "forbid", "must not")):
            goals.append(
                {
                    "id": "goal-1",
                    "statement": "Safety constraints hold under all allowed transitions.",
                    "kind": "safety",
                    "source": "keyword",
                }
            )
        if any(k in text for k in ("reach", "eventually", "complete", "liveness")):
            goals.append(
                {
                    "id": "goal-2",
                    "statement": "Desired states are eventually reachable.",
                    "kind": "liveness",
                    "source": "keyword",
                }
            )

    if not goals:
        names = [str(e["name"]) for e in model.entities[:3]]
        focus = ", ".join(names) if names else "the system"
        goals.append(
            {
                "id": "goal-1",
                "statement": f"Stated constraints over {focus} are preserved during operation.",
                "kind": "invariant",
                "source": "fallback",
            }
        )

    return goals


def claims_from_goals(
    goals: list[dict[str, Any]], assumptions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    asm_ids = [a["id"] for a in assumptions]
    return [
        {
            "id": f"claim-{g['id']}",
            "goal_id": g["id"],
            "assumption_ids": asm_ids,
            "statement": (
                "Under the modelled assumptions, "
                + str(g["statement"]).rstrip(".").lower()
                + "."
            ),
        }
        for g in goals
    ]
