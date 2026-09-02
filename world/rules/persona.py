"""Read-only persona handler over an entity's verbatim persona record.

``PersonaStore`` reads the opaque persona dict stored on ``entity.db.persona``
and exposes keyed retrieval plus bounded prompt-block flattening. String
values render on one labeled line; the structural keys ``identity``,
``appearance``, and ``social_connection`` render tolerantly: a mapping
becomes one ``子鍵：值`` line per renderable entry (known key groups follow
their declared order and localized sub-labels), a list or tuple becomes
dash-prefixed item lines, and any deeper nesting stringifies as a final
fallback; numbers, booleans, and ``None`` are skipped without ever raising.
``public_view()`` returns a new store over a copy whose mapping-valued
``identity`` has dropped its ``hidden`` sub-entry, so a player-facing block
excludes the hidden identity layer by construction. The handler carries no
write API, imports no state-mutating module, and never touches traits,
attributes beyond the single persona record, or the world clock. A missing,
malformed, or content-free record always degrades to ``None`` rather than
raising, so a persona can never break a look or a conversation.

``PersonaStore`` is read-only; persona records are written only by the import
loader, the ``world.rules`` deterministic services (activation and
``world.rules.persona_edit``), or the scene-builder characterization seam.
"""

import numbers
from collections.abc import Mapping
from types import SimpleNamespace
from typing import Any

# Hard bounds for LLM-bound persona text, following the project's ``_cap_string``
# idiom for deterministic truncation with an explicit marker. Callers may
# override both bounds and the flattened field set at the call site.
FIELD_LIMIT = 600
BLOCK_LIMIT = 2000

_TRUNCATION_MARKER = "…"

# Canonical Traditional Chinese labels for the flattened fields. ``background``
# is included only when explicitly requested by the caller; unknown fields fall
# back to their raw key as the label.
_FIELD_LABELS = {
    "personality": "性格：",
    "life_story": "人生經歷：",
    "habit": "習慣：",
    "background": "背景：",
    "identity": "身分：",
    "appearance": "外觀：",
    "social_connection": "人脈：",
}

# Declared rendering order for the known structural key groups (the character
# sheets' shapes); unrecognized sub-keys follow in insertion order.
_SUBKEY_ORDER = {
    "identity": ("public", "hidden"),
    "appearance": (
        "height",
        "weight",
        "measurement",
        "style",
        "overview",
        "attire",
        "feature",
    ),
}

# Localized sub-key labels where defined — the identity layers carry distinct
# 公開／隱秘 labels because the secret layer matters to the injection policy;
# every other sub-key renders with its raw key as the label.
_SUBKEY_LABELS = {
    "identity": {"public": "公開身分", "hidden": "隱秘身分"},
}

# Sentinel marking a subtree that the public-view prune must omit (a cycle
# back-reference); a module-private object, never stored on any record.
_DROP = object()


def _hidden_free_copy(value: Any, seen: frozenset[int]) -> Any:
    """Rebuild a hidden-free, cycle-safe copy of an opaque persona subtree.

    Every mapping is copied with its ``hidden``-keyed entries pruned at any
    depth, and every list or tuple is rebuilt element-wise, so the result
    shares no mutable container with the source and can never be re-poisoned
    by later mutations of the stored record. A cycle back-reference yields
    ``_DROP`` for that branch (the reference target's copy is already under
    construction); scalars pass through untouched.
    """
    if isinstance(value, Mapping):
        if id(value) in seen:
            return _DROP
        seen = seen | {id(value)}
        copy = {}
        for key, item in value.items():
            if key == "hidden":
                continue
            copied = _hidden_free_copy(item, seen)
            if copied is not _DROP:
                copy[key] = copied
        return copy
    if isinstance(value, (list, tuple)):
        if id(value) in seen:
            return _DROP
        seen = seen | {id(value)}
        items = []
        for item in value:
            copied = _hidden_free_copy(item, seen)
            if copied is not _DROP:
                items.append(copied)
        return items
    return value


class PersonaStore:
    """Read-only handler over an entity's verbatim persona record.

    Reads resolve against ``entity.db.persona`` and never persist anything;
    persona records are written only by the import loader, the ``world.rules``
    deterministic services, or the scene-builder characterization seam.
    """

    def __init__(
        self,
        entity: Any,
        *,
        field_limit: int = FIELD_LIMIT,
        block_limit: int = BLOCK_LIMIT,
    ) -> None:
        for name, limit in (("field_limit", field_limit), ("block_limit", block_limit)):
            if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
                raise ValueError(f"{name} must be a positive integer")
        self._entity = entity
        self._field_limit = field_limit
        self._block_limit = block_limit

    def _cap(self, value: str) -> str:
        if len(value) <= self._field_limit:
            return value
        return value[: self._field_limit - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER

    def get(self, field: str) -> Any | None:
        """Return ``field``'s stored value verbatim, or ``None`` when absent.

        A missing record, a non-mapping record, or a missing key all return
        ``None``; this never raises. Evennia materializes stored dicts as
        mapping wrappers, so any mapping counts as a record.
        """
        record = self._entity.db.persona
        if not isinstance(record, Mapping):
            return None
        return record.get(field)

    def public_view(self) -> "PersonaStore":
        """Return a read-only store over an independent hidden-free copy.

        When the record is a mapping whose ``identity`` value is itself a
        mapping, the copy holds a rebuilt identity subtree: ``hidden``-keyed
        entries are pruned at any depth, every nested container is a fresh
        copy (so later mutation of the stored record cannot re-introduce a
        hidden value), and cycle back-references are dropped from the copy.
        A block built through this view therefore excludes the hidden
        identity layer by construction rather than by post-hoc text
        scrubbing. A string-valued ``identity`` has no hidden layer and
        passes through verbatim; a missing or non-mapping record is carried
        through unchanged (flattening it still yields ``None``). The stored
        record is never mutated.
        """
        record = self._entity.db.persona
        view: Any = record
        if isinstance(record, Mapping):
            sanitized = dict(record)
            identity = sanitized.get("identity")
            if isinstance(identity, Mapping):
                sanitized["identity"] = _hidden_free_copy(identity, frozenset())
            view = sanitized
        holder = SimpleNamespace(db=SimpleNamespace(persona=view))
        return PersonaStore(
            holder, field_limit=self._field_limit, block_limit=self._block_limit
        )

    def flatten(
        self, fields: tuple[str, ...] = ("personality", "life_story", "habit")
    ) -> str | None:
        """Return one labeled prompt block for the present fields, or ``None``.

        Each present field produces a labeled section in the declared field
        order (e.g. ``性格：…`` / ``人生經歷：…`` / ``習慣：…``): a non-empty
        string renders on one capped line, a mapping renders ``子鍵：值``
        lines under its label, a list or tuple renders dash-prefixed item
        lines, deeper nesting stringifies, and numbers, booleans, or ``None``
        contribute nothing. Each section is capped and the combined block is
        capped at a total bound. A missing record, a non-mapping record, or a
        record with none of the requested fields renderable yields ``None``;
        this never raises.

        At configured bounds smaller than a label, the deterministic
        truncation may consume the label itself; the contract is only to
        bound the output, so callers are expected to pick usable bounds.
        """
        sections = []
        for field in fields:
            section = self._render_section(field, self.get(field))
            if section is not None:
                sections.append(section)
        if not sections:
            return None
        block = "\n".join(sections)
        if len(block) <= self._block_limit:
            return block
        return block[: self._block_limit - len(_TRUNCATION_MARKER)] + _TRUNCATION_MARKER

    def _render_section(self, field: str, value: Any) -> str | None:
        """Render one field value into its capped section, or ``None``.

        Strings keep the historical cap-before-label path; container sections
        are composed first and capped as a whole, so no emitted section can
        exceed the field bound.
        """
        label = _FIELD_LABELS.get(field, f"{field}：")
        if isinstance(value, str):
            if not value:
                return None
            return f"{label}{self._cap(value)}"
        if isinstance(value, Mapping):
            lines = self._render_entries(field, value)
            if not lines:
                return None
            return self._cap("\n".join([label, *lines]))
        if isinstance(value, (list, tuple)):
            items = self._render_items(value)
            if not items:
                return None
            return self._cap("\n".join([label, *items]))
        return None

    def _render_entries(self, field: str, mapping: Mapping) -> list[str]:
        """Render mapping sub-entries as ``子鍵：值`` lines, one level deep.

        Scalars (``None``, booleans, numbers) contribute nothing; a nested
        mapping is the deeper-nesting case and stringifies as the final
        fallback; list values expand into dash-prefixed item lines.
        """
        lines: list[str] = []
        sublabels = _SUBKEY_LABELS.get(field, {})
        for key in self._ordered_keys(field, mapping):
            value = mapping[key]
            label = sublabels.get(key, str(key))
            if isinstance(value, str):
                if value:
                    lines.append(f"{label}：{self._cap(value)}")
            elif isinstance(value, Mapping):
                lines.append(f"{label}：{self._cap(str(value))}")
            elif isinstance(value, (list, tuple)):
                items = self._render_items(value)
                if items:
                    lines.append(f"{label}：")
                    lines.extend(items)
        return lines

    def _render_items(self, sequence: Any) -> list[str]:
        """Render sequence items as dash-prefixed lines, skipping scalars.

        ``None`` and any number shape (int, float, bool, complex, Decimal,
        Fraction — anything the ``numbers`` hierarchy classifies) contribute
        no line; containers stringify as the final fallback.
        """
        lines: list[str] = []
        for item in sequence:
            if isinstance(item, str):
                if item:
                    lines.append(f"- {self._cap(item)}")
            elif item is None or isinstance(item, numbers.Number):
                continue
            else:
                lines.append(f"- {self._cap(str(item))}")
        return lines

    @staticmethod
    def _ordered_keys(field: str, mapping: Mapping) -> list[Any]:
        """Declared sub-key order for known groups, remaining keys after."""
        declared = _SUBKEY_ORDER.get(field)
        if declared is None:
            return list(mapping)
        head = [key for key in declared if key in mapping]
        tail = [key for key in mapping if key not in declared]
        return [*head, *tail]
