"""The authored NPC profile vocabulary: a stable key, a compact card, bounded voice lines.

A profile is referenced by its ``key``, never by its card's display name --
the key is the only stable handle a creation path, a place record, or a
later slice may hold. By convention a host profile's key equals its place's
``service_id`` (``npc-persona-host-examiner-producers`` enforces that rule;
this module only shapes the vocabulary, it does not check the convention).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from world.lore.npc_card import OFFLINE_GREETING_LIMIT, NpcCard, _normalize_text_leaf

# A profile key: a lowercase letter, then any run of lowercase letters,
# digits, or underscores, 1..64 code points total.
_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

# Each voice line is single-paragraph plain text. The bound is deliberately the
# per-instance offline-greeting bound: an authored greeting is the default the
# editable field replaces, so both must accept the same lines.
VOICE_LINE_LIMIT = OFFLINE_GREETING_LIMIT


@dataclass(frozen=True)
class NpcVoiceLines:
    """An authored profile's optional, bounded prewritten voice lines.

    ``greeting`` is the no-keyword topic line a creation path may show on
    first contact; ``misunderstood`` is the reply to an unrecognized
    keyword. Each non-``None`` line is normalized through the card leaf
    normalizer (CRLF/CR -> LF, outer whitespace stripped), then rejected
    when the normalized text still carries a newline (a voice line is a
    single paragraph) or exceeds ``VOICE_LINE_LIMIT`` code points.
    """

    greeting: str | None = None
    misunderstood: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("greeting", "misunderstood"):
            value = getattr(self, field_name)
            if value is None:
                continue
            normalized = _normalize_text_leaf(value, field_name)
            if "\n" in normalized:
                raise ValueError(
                    f"NpcVoiceLines.{field_name} must be a single paragraph (no newline)"
                )
            if len(normalized) > VOICE_LINE_LIMIT:
                raise ValueError(
                    f"NpcVoiceLines.{field_name} exceeds {VOICE_LINE_LIMIT} code points"
                )
            object.__setattr__(self, field_name, normalized)


@dataclass(frozen=True)
class NpcProfile:
    """One immutable authored NPC profile: a stable key, a card, and voice lines.

    Profiles are referenced by this key, never by the card's display name.
    By convention a host profile's key equals its place's ``service_id``
    (enforced by later slices, not here). Structural card validation (the
    compact card contract) is NOT performed here -- only that ``card`` is an
    ``NpcCard`` instance; full validation happens at registry assembly, so a
    malformed card can be reported naming the owning slice.
    """

    key: str
    card: NpcCard
    voice: NpcVoiceLines = NpcVoiceLines()

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not _KEY_RE.match(self.key):
            raise ValueError(
                f"NpcProfile key {self.key!r} must be a lowercase snake identifier "
                "(1..64 chars, starting with a letter)"
            )
        if not isinstance(self.card, NpcCard):
            raise ValueError(f"NpcProfile {self.key!r} card must be an NpcCard instance")
