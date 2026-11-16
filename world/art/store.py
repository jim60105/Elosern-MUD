"""Persistent carrier for one transient gallery generation job.

One ``GalleryJobRecord`` (an Evennia ``DefaultScript``) exists per REQUESTED
IMAGE, keyed ``art:<full-subject-key>:gen:<image-id>``. It carries only the
transient request state a claimed job needs and never a live object reference
or a committed output identity: its published artifact is a gallery card, and
the job is deleted the moment it reaches a terminal settle (design D1).
"""

from evennia import DefaultScript
from evennia.typeclasses.attributes import AttributeProperty


class ArtAssetStatus:
    """The ordered gallery-job lifecycle statuses."""

    MISSING = "missing"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"

    TERMINAL = (DONE, FAILED)
    ACTIVE = (PENDING, IN_PROGRESS)


class GalleryJobRecord(DefaultScript):
    """One transient per-image gallery job keyed ``art:<subject>:gen:<image>``."""

    kind: str = AttributeProperty(default="")
    subject_key: str = AttributeProperty(default="")
    source_description: str = AttributeProperty(default="")
    source_hash: str = AttributeProperty(default="")
    prompt_digest: str = AttributeProperty(default="")
    generation_token: str = AttributeProperty(default="")
    status: str = AttributeProperty(default=ArtAssetStatus.PENDING)
    attempt_count: int = AttributeProperty(default=0)
    last_error_code: str | None = AttributeProperty(default=None)
    enqueued_at: float | None = AttributeProperty(default=None)
    claimed_at: float | None = AttributeProperty(default=None)
    completed_at: float | None = AttributeProperty(default=None)
    aspect_ratio: str = AttributeProperty(default="")
    gallery_image_id: str = AttributeProperty(default="")
    gallery_binding: dict | None = AttributeProperty(default=None)
    gallery_face_rect: dict | None = AttributeProperty(default=None)
    gallery_requested_fields: list = AttributeProperty(default=list)
