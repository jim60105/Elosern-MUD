"""The closed per-kind gallery capability declaration, dependency-neutral by design.

``gallery-kind-capabilities`` commits exactly one immutable capability record
per ``ArtSubjectKind`` member: whether the kind has a gallery at all, the
store-path directory segment its stored identities use, the maximum number of
cards one gallery record may hold (``None`` means genuinely unbounded; only
``None`` and ``1`` are admitted), and whether its cards may carry equipment
bindings. A kind without a gallery — the scene kind — is declared explicitly
as such rather than represented by an absent entry, so "this kind has no
gallery" is an assertion in the table, not an accident of a missing key.

This module lives HERE — with zero imports — exactly like
``world/art/fallback_keys.py`` and for the same reason: ``world/art/subjects.py``
imports ``world/art/gallery_prompt.py`` at module level, so a capability table
that imported ``subjects`` would close an import cycle the moment the prompt
layer needed to consult it. The table is therefore keyed by the subject kind's
declared STRING value, never by the enum, and it performs no I/O, reads no
settings, and exposes no mutable state to consumers: the records and the table
view are frozen, and the writable origin is the module-private dict below,
which no consumer API hands out and which only the test patch seam rewrites —
the same kind resolves the same capabilities in every process.

Consumers (``gallery.py``, ``gallery_match.py``, ``queue.py``, ``worker.py``,
``gallery_seed.py``) decide every per-kind gallery rule by reading this
declaration instead of comparing subject kinds inline; the contract test
``validate_declaration_contract`` fails at test time if the table ever stops
covering the kind vocabulary exhaustively or names an illegal value.
"""

# The declared string value of ArtSubjectKind.SCENE (duplicated BY DESIGN —
# this module may not import world.art.subjects; the contract test fails if
# this literal ever diverges from the enum's value).
_SCENE_KIND_VALUE = "scene"
_CHARACTER_KIND_VALUE = "portrait:character"
_MONSTER_KIND_VALUE = "portrait:monster"


class GalleryKindCapabilities:
    """One immutable capability record for one subject kind value."""

    __slots__ = ("kind_value", "has_gallery", "store_directory", "max_cards", "supports_bindings")

    def __init__(
        self,
        kind_value: str,
        has_gallery: bool,
        store_directory: "str | None",
        max_cards: "int | None",
        supports_bindings: bool,
    ) -> None:
        object.__setattr__(self, "kind_value", kind_value)
        object.__setattr__(self, "has_gallery", has_gallery)
        object.__setattr__(self, "store_directory", store_directory)
        object.__setattr__(self, "max_cards", max_cards)
        object.__setattr__(self, "supports_bindings", supports_bindings)

    def __setattr__(self, name: str, value: object) -> "None":
        raise TypeError(
            f"gallery capability record for {self.kind_value!r} is immutable"
        )

    def __delattr__(self, name: str) -> "None":
        raise TypeError(
            f"gallery capability record for {self.kind_value!r} is immutable"
        )

    def __repr__(self) -> str:
        return (
            f"GalleryKindCapabilities(kind_value={self.kind_value!r}, "
            f"has_gallery={self.has_gallery!r}, "
            f"store_directory={self.store_directory!r}, "
            f"max_cards={self.max_cards!r}, "
            f"supports_bindings={self.supports_bindings!r})"
        )

    def with_values(self, **changes) -> "GalleryKindCapabilities":
        """A NEW record with these fields changed; this record stays frozen.

        Tests re-declare a kind's capabilities through this copy seam — the
        production table itself rejects mutation outright.
        """
        fields = {
            "kind_value": self.kind_value,
            "has_gallery": self.has_gallery,
            "store_directory": self.store_directory,
            "max_cards": self.max_cards,
            "supports_bindings": self.supports_bindings,
        }
        unknown = set(changes) - set(fields)
        if unknown:
            raise TypeError(
                f"unknown capability fields: {sorted(unknown)}"
            )
        fields.update(changes)
        return GalleryKindCapabilities(**fields)


class _ReadOnlyLookup:
    """The public read-only table: item access, iteration, and dict views.

    This is deliberately a read-only lookup view, NOT a general ``Mapping``:
    it exposes ``__getitem__``/``get``/``in``/iteration/``len`` plus fresh
    ``keys``/``values``/``items`` snapshots, and nothing else. Every read
    dereferences the module-private declaration at CALL time, so the view
    never retains a mutable dict of its own; every mutation attempt —
    ``__setitem__``, ``__delitem__``, attribute assignment — raises
    ``TypeError``.
    """

    __slots__ = ()

    def __getitem__(self, key: str) -> object:
        return _CAPABILITIES_BY_KIND_VALUE[key]

    def get(self, key: str, default: object = None) -> object:
        return _CAPABILITIES_BY_KIND_VALUE.get(key, default)

    def __contains__(self, key: object) -> bool:
        return key in _CAPABILITIES_BY_KIND_VALUE

    def __iter__(self):
        return iter(_CAPABILITIES_BY_KIND_VALUE)

    def __len__(self) -> int:
        return len(_CAPABILITIES_BY_KIND_VALUE)

    def keys(self):
        return tuple(_CAPABILITIES_BY_KIND_VALUE)

    def values(self):
        return tuple(_CAPABILITIES_BY_KIND_VALUE.values())

    def items(self):
        return tuple(_CAPABILITIES_BY_KIND_VALUE.items())

    def __setitem__(self, key: str, value: object) -> "None":
        raise TypeError("the gallery capability table is immutable")

    def __delitem__(self, key: str) -> "None":
        raise TypeError("the gallery capability table is immutable")

    def __setattr__(self, name: str, value: object) -> "None":
        raise TypeError("the gallery capability table is immutable")

    def __delattr__(self, name: str) -> "None":
        raise TypeError("the gallery capability table is immutable")

    def __repr__(self) -> str:
        return f"ReadOnlyLookup({_CAPABILITIES_BY_KIND_VALUE!r})"


# THE ONE DECLARATION: exactly one immutable record per ArtSubjectKind member,
# keyed by the kind's declared string value. `character` declares a null
# maximum — it is uncapped today and stays uncapped; `monster` declares the
# one-card cap without binding support; `scene` is declared explicitly as
# having no gallery. Only None and 1 are admitted as maxima (enforced by
# validate_declaration_contract below); the contract test rejects anything
# else, so no real declaration needs an N-card eviction algorithm.
_CAPABILITIES_BY_KIND_VALUE: dict = {
    _CHARACTER_KIND_VALUE: GalleryKindCapabilities(
        kind_value=_CHARACTER_KIND_VALUE,
        has_gallery=True,
        store_directory="character",
        max_cards=None,
        supports_bindings=True,
    ),
    _MONSTER_KIND_VALUE: GalleryKindCapabilities(
        kind_value=_MONSTER_KIND_VALUE,
        has_gallery=True,
        store_directory="monster",
        max_cards=1,
        supports_bindings=False,
    ),
    _SCENE_KIND_VALUE: GalleryKindCapabilities(
        kind_value=_SCENE_KIND_VALUE,
        has_gallery=False,
        store_directory=None,
        max_cards=None,
        supports_bindings=False,
    ),
}

# The public, immutable view of the table.
GALLERY_KIND_CAPABILITIES = _ReadOnlyLookup()


def gallery_store_directory_segments() -> "frozenset[str]":
    """The CLOSED set of gallery-bearing store directory segments.

    Derived fresh from the declaration at call time (the seed traversal and
    the store-path vocabulary share this one origin; a no-gallery kind
    contributes nothing here).
    """
    return frozenset(
        record.store_directory
        for record in _CAPABILITIES_BY_KIND_VALUE.values()
        if record.has_gallery
    )


def _kind_value_of(kind: object) -> str:
    """The declared string value for an enum member or a plain string key."""
    return getattr(kind, "value", kind)


def capabilities_for(kind: object) -> GalleryKindCapabilities:
    """The capability record for a subject kind value (or kind member).

    Raises ``KeyError`` naming the value for anything the declaration does not
    cover — an undeclared kind is a loud failure, never a silent ``None``.
    """
    key = _kind_value_of(kind)
    record = _CAPABILITIES_BY_KIND_VALUE.get(key)
    if record is None:
        raise KeyError(f"no gallery capability declared for kind {key!r}")
    return record


def has_gallery(kind: object) -> bool:
    """True when the kind's declaration grants it a gallery at all."""
    return capabilities_for(kind).has_gallery


def store_directory_for(kind: object) -> str:
    """The store directory segment a gallery-bearing kind's identities use.

    Raises ``KeyError`` for a kind declared without a gallery — a caller
    reaching this accessor for such a kind is a bug it must hear about loudly.
    """
    record = capabilities_for(kind)
    if not record.has_gallery:
        raise KeyError(f"kind {record.kind_value!r} declares no gallery directory")
    return record.store_directory


def kind_value_for_store_directory(directory: object) -> "str | None":
    """The gallery-bearing kind value owning a store directory, else ``None``.

    The reverse lookup the seed traversal uses; a no-gallery kind's name (e.g.
    ``scene``) is deliberately NOT in the reverse vocabulary and resolves to
    ``None`` exactly as it did under the previous directory dict.
    """
    key = _kind_value_of(directory)
    for value, record in _CAPABILITIES_BY_KIND_VALUE.items():
        if record.has_gallery and record.store_directory == key:
            return value
    return None


# The admitted declared card maxima: null (genuinely unbounded) or exactly 1.
# A future kind that genuinely needs an intermediate cap widens this rule in
# the change that introduces it.
ADMITTED_MAXIMA = (None, 1)


def _is_admitted_maximum(value: object) -> bool:
    """True only for literal ``None`` or the exact ``int`` 1.

    ``True in (None, 1)`` and ``1.0 in (None, 1)`` are both true in Python —
    so membership is never good enough: booleans and floats are rejected by
    type here.
    """
    return value is None or (type(value) is int and value == 1)


def validate_declaration_contract(kind_values: "tuple[str, ...]") -> list:
    """Return every violation between the table and a subject-kind vocabulary.

    Empty means the contract holds. Each violation string names the offending
    kind (and value), so the contract test fails with a diagnosis:
    an undeclared kind, a stale entry naming no member, a declared maximum
    outside the admitted values, or a cross-field impossibility (a gallery
    without a directory, a no-gallery kind claiming a directory, a maximum, or
    binding support, a record whose own kind_value disagrees with its key, or
    a flag that is not exactly a bool).
    """
    violations = []
    declared = set(_CAPABILITIES_BY_KIND_VALUE)
    vocabulary = set(kind_values)
    for value in sorted(vocabulary - declared):
        violations.append(f"subject kind {value!r} has no gallery capability declaration")
    for value in sorted(declared - vocabulary):
        violations.append(f"gallery capability entry {value!r} names no subject kind")
    for value in sorted(declared & vocabulary):
        record = _CAPABILITIES_BY_KIND_VALUE[value]
        if record.kind_value != value:
            violations.append(
                f"gallery capability entry keyed {value!r} declares "
                f"kind_value {record.kind_value!r}"
            )
        if not isinstance(record.has_gallery, bool):
            violations.append(
                f"kind {value!r} declares has_gallery "
                f"{record.has_gallery!r}, not a bool"
            )
        if not isinstance(record.supports_bindings, bool):
            violations.append(
                f"kind {value!r} declares supports_bindings "
                f"{record.supports_bindings!r}, not a bool"
            )
        if not _is_admitted_maximum(record.max_cards):
            violations.append(
                f"kind {value!r} declares card maximum {record.max_cards!r} "
                f"outside the admitted values (None or exactly the int 1)"
            )
        if record.has_gallery:
            if not isinstance(record.store_directory, str) or not record.store_directory:
                violations.append(
                    f"gallery-bearing kind {value!r} declares no store directory"
                )
        else:
            if record.store_directory is not None:
                violations.append(
                    f"no-gallery kind {value!r} declares store directory "
                    f"{record.store_directory!r}"
                )
            if record.max_cards is not None:
                violations.append(
                    f"no-gallery kind {value!r} declares card maximum "
                    f"{record.max_cards!r}"
                )
            if record.supports_bindings:
                violations.append(
                    f"no-gallery kind {value!r} declares binding support"
                )
    return violations


__all__ = [
    "ADMITTED_MAXIMA",
    "GALLERY_KIND_CAPABILITIES",
    "GalleryKindCapabilities",
    "capabilities_for",
    "gallery_store_directory_segments",
    "has_gallery",
    "kind_value_for_store_directory",
    "store_directory_for",
    "validate_declaration_contract",
]
