"""The frozen ``BeatProposal`` value vocabulary (design §7, story-director-beats).

A director decision yields at most one *beat proposal*: the generative layer's
value-only intent for continuing a story. A proposal carries intent only — the
deterministic core decides which effect a kind materializes and whether any
deterministic owner implements it, so no proposal can name its own routing or
claim a state write.

Immutability is enforced by construction: ``__post_init__`` rejects any mutable
container nested under the value, so a proposal is safe to hand across the
``world/ai`` boundary unchanged. This module imports no state writer, no
typeclass, and no live transport (``tests/test_ai_transport_contract.py``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from world.ai.immutable import (
    reject_mutable_containers as _reject_mutable_containers,
)

# The closed beat-kind vocabulary. A kind names the shape of the intended
# continuation; the deterministic core maps it to an effect and decides whether
# that effect has an implemented owner (quest seeds do not, yet).
BEAT_KIND_FOLLOW_UP = "follow_up"
BEAT_KIND_CLUE = "clue"
BEAT_KIND_INVITATION = "invitation"
BEAT_KIND_LETTER = "letter"
BEAT_KIND_QUEST_SEED = "quest_seed"

BEAT_KINDS: frozenset[str] = frozenset(
    {
        BEAT_KIND_FOLLOW_UP,
        BEAT_KIND_CLUE,
        BEAT_KIND_INVITATION,
        BEAT_KIND_LETTER,
        BEAT_KIND_QUEST_SEED,
    }
)

# Hard proposal bounds, mirrored by the output schema and the semantic
# validators so a pathological response cannot produce an unbounded write.
MAX_SUMMARY_CHARACTERS = 600
MAX_RECIPIENT_CHARACTERS = 128
MAX_WRITE_CLAIMS = 8
MAX_WRITE_CLAIM_CHARACTERS = 64
MAX_RELATION_DELTA = 10

_CJK_START = "\u4e00"
_CJK_END = "\u9fff"


def has_cjk(text: str) -> bool:
    """True when the text contains at least one Han character."""
    return any(_CJK_START <= char <= _CJK_END for char in text)


@dataclass(frozen=True)
class BeatProposal:
    """One value-only beat intent; never a live object or a writer request."""

    kind: str
    summary: str
    recipient: str = ""
    relation_delta: int = 0
    writes: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        _reject_mutable_containers(self, type(self).__name__)
        if self.kind not in BEAT_KINDS:
            raise ValueError(f"beat kind {self.kind!r} is outside {sorted(BEAT_KINDS)}")
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise ValueError("beat summary must be non-empty prose")
        if len(self.summary) > MAX_SUMMARY_CHARACTERS:
            raise ValueError(
                f"beat summary exceeds {MAX_SUMMARY_CHARACTERS} characters"
            )
        if len(str(self.recipient)) > MAX_RECIPIENT_CHARACTERS:
            raise ValueError(
                f"beat recipient exceeds {MAX_RECIPIENT_CHARACTERS} characters"
            )
        if isinstance(self.relation_delta, bool) or not isinstance(
            self.relation_delta, int
        ):
            raise ValueError("beat relation_delta must be an integer")
        if not 0 <= self.relation_delta <= MAX_RELATION_DELTA:
            raise ValueError(
                f"beat relation_delta must be within 0..{MAX_RELATION_DELTA}"
            )
        if len(self.writes) > MAX_WRITE_CLAIMS or any(
            not isinstance(claim, str) or len(claim) > MAX_WRITE_CLAIM_CHARACTERS
            for claim in self.writes
        ):
            raise ValueError("beat write claims must be bounded strings")

    @classmethod
    def from_payload(cls, payload: Any) -> "BeatProposal":
        """Build a proposal from a schema-validated plain payload.

        Raises ``ValueError``/``TypeError``/``KeyError`` on a shape the
        deterministic core must never receive; the generation entry point maps
        that to a no-content outcome rather than a fabricated beat.
        """
        if not isinstance(payload, Mapping):
            raise TypeError("beat proposal payload must be a mapping")
        kind = payload["kind"]
        if not isinstance(kind, str):
            raise TypeError("beat kind must be a string")
        summary = payload["summary"]
        if not isinstance(summary, str):
            raise TypeError("beat summary must be a string")
        recipient = payload.get("recipient", "")
        if recipient is None:
            recipient = ""
        if not isinstance(recipient, str):
            raise TypeError("beat recipient must be a string")
        raw_delta = payload.get("relation_delta", 0)
        if raw_delta is None:
            raw_delta = 0
        if isinstance(raw_delta, bool) or not isinstance(raw_delta, int):
            raise TypeError("beat relation_delta must be an integer")
        raw_writes = payload.get("writes")
        if raw_writes is None:
            raw_writes = ()
        if not isinstance(raw_writes, (list, tuple)):
            raise TypeError("beat writes must be a list")
        return cls(
            kind=kind,
            summary=summary.strip(),
            recipient=recipient.strip(),
            relation_delta=raw_delta,
            writes=tuple(raw_writes),
        )
