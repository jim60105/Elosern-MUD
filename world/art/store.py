"""Persistent asset-record contract for generated art outputs.

One ``ArtAssetRecord`` (an Evennia ``DefaultScript``) exists per subject key.
It carries the full deterministic record contract and never a live object
reference, mirroring the idempotent lore-mirror pattern ``world/lore/sync.py``
uses (design D4).
"""

from evennia import DefaultScript
from evennia.typeclasses.attributes import AttributeProperty


class ArtAssetStatus:
    """The ordered art-record lifecycle statuses."""

    MISSING = "missing"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"

    TERMINAL = (DONE, FAILED)
    ACTIVE = (PENDING, IN_PROGRESS)


# Status advancement rank used by duplicate consolidation: keep the most
# advanced record when the same subject somehow has more than one.
_STATUS_RANK = {
    ArtAssetStatus.MISSING: 0,
    ArtAssetStatus.PENDING: 1,
    ArtAssetStatus.IN_PROGRESS: 2,
    ArtAssetStatus.FAILED: 3,
    ArtAssetStatus.DONE: 4,
}


def status_rank(status: str) -> int:
    """Return the advancement rank of an art status for consolidation."""
    return _STATUS_RANK.get(status, 0)


class ArtAssetRecord(DefaultScript):
    """One persistent art record keyed ``art:<full-subject-key>``."""

    kind: str = AttributeProperty(default="")
    subject_key: str = AttributeProperty(default="")
    source_description: str = AttributeProperty(default="")
    source_hash: str = AttributeProperty(default="")
    prompt_digest: str = AttributeProperty(default="")
    generation_token: str = AttributeProperty(default="")
    status: str = AttributeProperty(default=ArtAssetStatus.MISSING)
    output_identity: str | None = AttributeProperty(default=None)
    prior_output_identity: str | None = AttributeProperty(default=None)
    attempt_count: int = AttributeProperty(default=0)
    last_error_code: str | None = AttributeProperty(default=None)
    enqueued_at: float | None = AttributeProperty(default=None)
    claimed_at: float | None = AttributeProperty(default=None)
    completed_at: float | None = AttributeProperty(default=None)
    aspect_ratio: str = AttributeProperty(default="")
    hash_changed: bool = AttributeProperty(default=False)
    # The server-reported generation seed of the CURRENT output (nullable:
    # servers may not report one). settle_generated assigns it unconditionally
    # on publish, so a seedless regeneration never keeps a stale seed.
    seed: int | None = AttributeProperty(default=None)
