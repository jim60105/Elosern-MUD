"""The closed built-in fallback-key vocabulary, dependency-neutral by design.

``gallery-builtin-fallbacks`` commits exactly one image per key of this
vocabulary into the in-repo defaults directory served through the
``/art/defaults/<key>.<ext>`` route. The vocabulary, the single committed
extension, and the per-file size bound live HERE — in a module that imports
nothing — because both sides of the contract need the exact same constants:

* ``world/art/gallery_fallback.py`` (the resolver) and ``web/art_media.py``
  (the serving route) consume the closed set so a key can never resolve to a
  missing image and a stray file can never be served;
* the lore registries (player presets, NPC tiers, monster tiers) validate an
  OPTIONAL declared fallback key at registry construction time, and lore must
  never import the rest of ``world.art`` — this module is the only
  ``world.art`` surface lore is allowed to touch, precisely because it is
  side-effect-free data with zero imports.

Resolution itself (declaration, band, hash) lives in
``world/art/gallery_fallback.py``; this module carries only the vocabulary.
"""

from __future__ import annotations

# The CLOSED fallback-key vocabulary (design §7.2). Exactly one committed
# image exists per key, and nothing outside this set is ever served or
# resolvable. Monster subjects always resolve ``monster_anon``.
FALLBACK_KEYS: frozenset[str] = frozenset(
    {"man", "woman", "boy", "girl", "elder", "monster_anon"}
)

# The one extension the committed defaults use (the sd-webui wire format is
# PNG; the committed files are converted to bounded-size WebP).
FALLBACK_EXTENSION = ".webp"

# The declared size bound every committed fallback image must stay under
# (400 KiB), enforced in both directions by the contract test.
FALLBACK_MAX_FILE_BYTES = 409_600

# The fixed in-repo defaults directory, relative to the repository root
# (``web/static`` is the first STATICFILES_DIRS entry).
FALLBACK_DEFAULTS_DIRECTORY = "web/static/art/defaults"

__all__ = [
    "FALLBACK_DEFAULTS_DIRECTORY",
    "FALLBACK_EXTENSION",
    "FALLBACK_KEYS",
    "FALLBACK_MAX_FILE_BYTES",
    "validate_fallback_key",
]


def validate_fallback_key(value: object, owner: str) -> None:
    """Reject a declared fallback key outside the closed vocabulary.

    ``None`` is legal — every registry entry MAY omit the declaration and
    stays valid without one. Anything else must be an exact vocabulary
    member, so a typo raises at registry construction (import) time naming
    the owning entry rather than silently shipping a key that could never
    resolve to a committed image.
    """
    if value is None:
        return
    if value not in FALLBACK_KEYS:
        raise ValueError(
            f"{owner} declares fallback key {value!r} outside the closed "
            f"fallback vocabulary {sorted(FALLBACK_KEYS)}"
        )
