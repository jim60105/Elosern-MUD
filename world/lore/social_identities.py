"""Frozen social identity domain vocabulary and read-only registry.

Declares the closed vocabulary of social identity membership tags.
These are membership tags, with no numeric rank/order and no race-derived
assignment.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


MAX_SOCIAL_IDENTITIES = 8


@dataclass(frozen=True)
class SocialIdentity:
    """One immutable social identity tag."""

    key: str
    display_name_zh: str

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not self.key.strip():
            raise ValueError("SocialIdentity key must be a non-empty string")
        if not isinstance(self.display_name_zh, str) or not self.display_name_zh.strip():
            raise ValueError("SocialIdentity display_name_zh must be a non-empty string")


SOCIAL_IDENTITY_REGISTRY: MappingProxyType[str, SocialIdentity] = MappingProxyType(
    {
        "noble": SocialIdentity("noble", "貴族"),
        "clergy": SocialIdentity("clergy", "神職人員"),
        "official": SocialIdentity("official", "官員"),
        "adventurer": SocialIdentity("adventurer", "冒險者"),
    }
)
