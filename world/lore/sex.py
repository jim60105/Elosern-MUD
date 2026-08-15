"""Single source of truth for the entity sex vocabulary.

``CHARACTER_SCHEMA_V1`` (import validation) and ``LivingEntity.sex`` (the
typeclass attribute default) are the current consumers.  The later act-catalog
change must import these constants rather than redefining their values.
"""

SEX_VALUES = ("female", "male", "other")
DEFAULT_SEX = "other"

__all__ = ["DEFAULT_SEX", "SEX_VALUES"]
