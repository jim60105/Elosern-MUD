"""Pure compact NPC character card contract and validation (D1/D3).

This module defines the compact NPC character card structure, leaf-level and
whole-block length bounds, plain-text normalization, stable error codes,
rendering order, budget calculations, and closed provenance vocabulary.

Architectural boundary: This module lives in ``world/lore/`` and MUST NOT
import anything from Evennia, Django, or ``world/rules/``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

# Format and content generation versions (D1/D3)
NPC_CARD_FORMAT: int = 1
NPC_PERSONA_CONTENT_GENERATION: int = 1

# Length bounds (in Unicode code points)
LEAF_LIMIT: int = 600
IDENTITY_SECTION_LIMIT: int = 600
CARD_BLOCK_LIMIT: int = 2000

# The per-instance offline greeting (``db.npc_offline_greeting``): one
# single-paragraph plain-text line, bounded like an authored voice line. It is
# not a card leaf and never counts toward ``CARD_BLOCK_LIMIT``.
OFFLINE_GREETING_LIMIT: int = 300

# Top-level storage key set
NPC_CARD_FIELDS: frozenset[str] = frozenset({
    "identity",
    "appearance",
    "personality",
    "speech_style",
    "life_story",
    "habit",
    "social_connection",
})

# Canonical rendering order
NPC_CARD_RENDER_ORDER: tuple[str, ...] = (
    "identity",
    "appearance",
    "personality",
    "speech_style",
    "life_story",
    "habit",
    "social_connection",
)

# Required text leaves
REQUIRED_TEXT_LEAVES: frozenset[str] = frozenset({
    "identity.public",
    "appearance",
    "personality",
    "speech_style",
    "life_story",
    "habit",
})

# Optional text leaves (persist as "" when empty)
OPTIONAL_TEXT_LEAVES: frozenset[str] = frozenset({
    "identity.hidden",
    "social_connection",
})

# Field labels for rendering
_CARD_FIELD_LABELS: MappingProxyType[str, str] = MappingProxyType(dict([
    ("identity", "身分："),
    ("appearance", "外觀："),
    ("personality", "性格："),
    ("speech_style", "說話風格："),
    ("life_story", "人生經歷："),
    ("habit", "習慣："),
    ("social_connection", "人脈："),
]))

# Subkey labels for identity
_CARD_IDENTITY_LABELS: MappingProxyType[str, str] = MappingProxyType(dict([
    ("public", "公開身分"),
    ("hidden", "隱秘身分"),
]))

# Closed provenance kinds and their allowed keys
PROVENANCE_KINDS: frozenset[str] = frozenset({
    "profile",
    "companion",
    "import",
    "generated_quest",
    "offline_bundle",
})

# Maximum length for an identifier string in provenance (never prose)
PROVENANCE_IDENTIFIER_LIMIT: int = 120

_CRLF_RE = re.compile(r"\r\n|\r")

# Finite boundary whitespace set: U+0009–U+000D, U+0020, U+0085, U+00A0, U+1680,
# U+2000–U+200A, U+2028, U+2029, U+202F, U+205F, U+3000, U+FEFF.
# Explicitly excludes U+001C–U+001F, U+180E, U+200B, U+2060.
NPC_BOUNDARY_WHITESPACE: str = (
    "\u0009\u000a\u000b\u000c\u000d"
    "\u0020"
    "\u0085"
    "\u00a0"
    "\u1680"
    "\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a"
    "\u2028\u2029"
    "\u202f"
    "\u205f"
    "\u3000"
    "\ufeff"
)
NPC_BOUNDARY_WHITESPACE_CHARS: frozenset[str] = frozenset(NPC_BOUNDARY_WHITESPACE)


def normalize_npc_text(val: str) -> str:
    """Normalize line endings (CRLF/CR -> LF) and strip explicit finite boundary whitespace."""
    return _CRLF_RE.sub("\n", val).strip(NPC_BOUNDARY_WHITESPACE)


class NpcCardError(ValueError):
    """Raised when an NPC card or provenance fails validation.

    Attributes:
        code: Stable error code string.
        field: Name of the offending leaf or key, or None if root/block-wide.
    """

    def __init__(self, code: str, field: str | None = None) -> None:
        self.code = code
        self.field = field
        msg = f"{code}: {field}" if field else code
        super().__init__(msg)


@dataclass(frozen=True)
class NpcCardIdentity:
    public: str
    hidden: str = ""

    def to_record(self) -> dict[str, str]:
        return {"public": self.public, "hidden": self.hidden}


@dataclass(frozen=True)
class NpcCard:
    """Frozen representation of a validated compact NPC character card."""

    identity: NpcCardIdentity
    appearance: str
    personality: str
    speech_style: str
    life_story: str
    habit: str
    social_connection: str = ""

    def to_record(self) -> dict[str, Any]:
        """Produce the exact dictionary persisted in entity.db.persona."""
        return {
            "identity": self.identity.to_record(),
            "appearance": self.appearance,
            "personality": self.personality,
            "speech_style": self.speech_style,
            "life_story": self.life_story,
            "habit": self.habit,
            "social_connection": self.social_connection,
        }

    @classmethod
    def from_record(cls, record: Any) -> NpcCard:
        """Validate and construct an NpcCard from an input record."""
        return normalize_card(record)


@dataclass(frozen=True)
class CardBudget:
    """Budget measurement of an NPC character card."""

    per_leaf: dict[str, int]
    identity_section: int
    total: int
    remaining_total: int


def _normalize_text_leaf(val: Any, field_name: str) -> str:
    """Validate that val is a string, normalize line endings and outer whitespace."""
    if not isinstance(val, str) or isinstance(val, bool):
        raise NpcCardError("not_text", field_name)
    return normalize_npc_text(val)


def render_identity_section(public: str, hidden: str) -> str:
    """Render the identity section in canonical format.

    Format matches PersonaStore:
    身分：
    公開身分：<public>
    隱秘身分：<hidden>   (omitted if hidden is empty)
    """
    lines = [f"{_CARD_FIELD_LABELS['identity']}"]
    lines.append(f"{_CARD_IDENTITY_LABELS['public']}：{public}")
    if hidden:
        lines.append(f"{_CARD_IDENTITY_LABELS['hidden']}：{hidden}")
    return "\n".join(lines)


def render_card_block(card: NpcCard) -> str:
    """Render the full labeled card block in NPC_CARD_RENDER_ORDER.

    Matches PersonaStore.flatten(NPC_CARD_RENDER_ORDER) exactly.
    Empty optional sections (identity.hidden, social_connection) contribute no line/section.
    Sections are joined by single newline.
    """
    sections: list[str] = []
    for field in NPC_CARD_RENDER_ORDER:
        if field == "identity":
            sec = render_identity_section(card.identity.public, card.identity.hidden)
            sections.append(sec)
        elif field == "social_connection":
            if card.social_connection:
                sections.append(f"{_CARD_FIELD_LABELS[field]}{card.social_connection}")
        else:
            val = getattr(card, field)
            sections.append(f"{_CARD_FIELD_LABELS[field]}{val}")
    return "\n".join(sections)


def card_budget(card: NpcCard) -> CardBudget:
    """Calculate the budget breakdown and remaining room for a card."""
    per_leaf = {
        "identity.public": len(card.identity.public),
        "identity.hidden": len(card.identity.hidden),
        "appearance": len(card.appearance),
        "personality": len(card.personality),
        "speech_style": len(card.speech_style),
        "life_story": len(card.life_story),
        "habit": len(card.habit),
        "social_connection": len(card.social_connection),
    }
    ident_sec = render_identity_section(card.identity.public, card.identity.hidden)
    ident_len = len(ident_sec)
    rendered_total = len(render_card_block(card))
    return CardBudget(
        per_leaf=per_leaf,
        identity_section=ident_len,
        total=rendered_total,
        remaining_total=CARD_BLOCK_LIMIT - rendered_total,
    )


def normalize_card(raw: Any) -> NpcCard:
    """Validate, normalize, and construct an NpcCard from raw input.

    Raises:
        NpcCardError: with stable error codes and field names.
    """
    if not isinstance(raw, Mapping) or isinstance(raw, (str, bytes)):
        raise NpcCardError("card_not_object", None)

    raw_keys = set(raw.keys())
    unknown_keys = raw_keys - NPC_CARD_FIELDS
    if unknown_keys:
        # Report the first alphabetically or sorted for deterministic output
        first_unknown = sorted(str(k) for k in unknown_keys)[0]
        raise NpcCardError("unknown_field", first_unknown)

    missing_keys = NPC_CARD_FIELDS - raw_keys
    if missing_keys:
        # Check in render order for determinism
        for k in NPC_CARD_RENDER_ORDER:
            if k in missing_keys:
                raise NpcCardError("missing_field", k)

    # Validate identity structure
    raw_identity = raw.get("identity")
    if not isinstance(raw_identity, Mapping) or isinstance(raw_identity, (str, bytes)):
        raise NpcCardError("not_text", "identity")

    ident_keys = set(raw_identity.keys())
    allowed_ident_keys = {"public", "hidden"}
    unknown_ident_keys = ident_keys - allowed_ident_keys
    if unknown_ident_keys:
        first_ident_unknown = sorted(str(k) for k in unknown_ident_keys)[0]
        raise NpcCardError("unknown_field", f"identity.{first_ident_unknown}")

    missing_ident_keys = allowed_ident_keys - ident_keys
    if missing_ident_keys:
        for k in ("public", "hidden"):
            if k in missing_ident_keys:
                raise NpcCardError("missing_field", f"identity.{k}")

    # Normalize identity leaves
    norm_public = _normalize_text_leaf(raw_identity["public"], "identity.public")
    if not norm_public:
        raise NpcCardError("required_empty", "identity.public")
    if len(norm_public) > LEAF_LIMIT:
        raise NpcCardError("leaf_too_long", "identity.public")

    norm_hidden = _normalize_text_leaf(raw_identity["hidden"], "identity.hidden")
    if len(norm_hidden) > LEAF_LIMIT:
        raise NpcCardError("leaf_too_long", "identity.hidden")

    # Identity section length bound
    ident_rendered = render_identity_section(norm_public, norm_hidden)
    if len(ident_rendered) > IDENTITY_SECTION_LIMIT:
        raise NpcCardError("identity_section_too_long", "identity")

    # Normalize other leaves
    leaves: dict[str, str] = {}
    for field in ("appearance", "personality", "speech_style", "life_story", "habit"):
        val = _normalize_text_leaf(raw[field], field)
        if not val:
            raise NpcCardError("required_empty", field)
        if len(val) > LEAF_LIMIT:
            raise NpcCardError("leaf_too_long", field)
        leaves[field] = val

    # Optional social_connection
    social = _normalize_text_leaf(raw["social_connection"], "social_connection")
    if len(social) > LEAF_LIMIT:
        raise NpcCardError("leaf_too_long", "social_connection")
    leaves["social_connection"] = social

    card = NpcCard(
        identity=NpcCardIdentity(public=norm_public, hidden=norm_hidden),
        appearance=leaves["appearance"],
        personality=leaves["personality"],
        speech_style=leaves["speech_style"],
        life_story=leaves["life_story"],
        habit=leaves["habit"],
        social_connection=leaves["social_connection"],
    )

    rendered_block = render_card_block(card)
    if len(rendered_block) > CARD_BLOCK_LIMIT:
        raise NpcCardError("card_too_long", None)

    return card


def normalize_offline_greeting(raw: Any) -> str:
    """Validate and normalize an editor-submitted offline greeting.

    The text is normalized exactly like a card leaf (CRLF/CR to LF, outer
    whitespace trimmed). The empty string is valid and means "no override".
    Non-text input, a normalized value longer than ``OFFLINE_GREETING_LIMIT``
    code points, or one that still contains a newline (more than one
    paragraph) raises ``NpcCardError("greeting_invalid", "offline_greeting")``.
    """
    if not isinstance(raw, str) or isinstance(raw, bool):
        raise NpcCardError("greeting_invalid", "offline_greeting")
    normalized = normalize_npc_text(raw)
    if "\n" in normalized or len(normalized) > OFFLINE_GREETING_LIMIT:
        raise NpcCardError("greeting_invalid", "offline_greeting")
    return normalized


def validate_provenance(provenance: Any) -> dict[str, Any]:
    """Validate initialization provenance dictionary.

    Returns the validated provenance dictionary.
    Raises NpcCardError on violation.
    """
    if not isinstance(provenance, Mapping) or isinstance(provenance, (str, bytes)):
        raise NpcCardError("invalid_provenance", "provenance")

    kind = provenance.get("kind")
    if not isinstance(kind, str) or kind not in PROVENANCE_KINDS:
        raise NpcCardError("invalid_provenance", "kind")

    def _check_id_str(val: Any, field_name: str) -> str:
        if not isinstance(val, str) or isinstance(val, bool) or not val:
            raise NpcCardError("invalid_provenance", field_name)
        if len(val) > PROVENANCE_IDENTIFIER_LIMIT:
            raise NpcCardError("invalid_provenance", field_name)
        return val

    def _check_int(val: Any, field_name: str) -> int:
        if not isinstance(val, int) or isinstance(val, bool) or val < 0:
            raise NpcCardError("invalid_provenance", field_name)
        return val

    validated: dict[str, Any] = {"kind": kind}

    if kind == "profile":
        if set(provenance.keys()) != {"kind", "profile"}:
            raise NpcCardError("invalid_provenance", "profile")
        validated["profile"] = _check_id_str(provenance.get("profile"), "profile")

    elif kind == "companion":
        if set(provenance.keys()) != {"kind", "profile", "owner"}:
            raise NpcCardError("invalid_provenance", "companion")
        validated["profile"] = _check_id_str(provenance.get("profile"), "profile")
        validated["owner"] = _check_int(provenance.get("owner"), "owner")

    elif kind == "import":
        if set(provenance.keys()) != {"kind", "record"}:
            raise NpcCardError("invalid_provenance", "import")
        validated["record"] = _check_id_str(provenance.get("record"), "record")

    elif kind == "generated_quest":
        if set(provenance.keys()) != {"kind", "quest", "stage", "occupant"}:
            raise NpcCardError("invalid_provenance", "generated_quest")
        validated["quest"] = _check_id_str(provenance.get("quest"), "quest")
        validated["stage"] = _check_int(provenance.get("stage"), "stage")
        validated["occupant"] = _check_int(provenance.get("occupant"), "occupant")

    elif kind == "offline_bundle":
        if set(provenance.keys()) != {"kind", "pool", "bundle"}:
            raise NpcCardError("invalid_provenance", "offline_bundle")
        validated["pool"] = _check_id_str(provenance.get("pool"), "pool")
        validated["bundle"] = _check_id_str(provenance.get("bundle"), "bundle")

    return validated
