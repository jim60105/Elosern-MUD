"""Reference declarations on authored registry dataclass fields (gm-portal-s4 §3.1).

A leaf module with no game imports, so every registry module (and the quest
definitions) can declare references without an import cycle. A declaration is
plain ``dataclasses.field`` metadata: it changes no field type, default or
value, and nothing at startup reads it. ``world.lore.registry_index`` walks the
declarations to build the forward and inverse reference maps the GM portal
browses, and the CI contract checks every declared key exists.

    @dataclass(frozen=True)
    class MonsterSite:
        region_key: str = field(metadata=ref("wilderness_regions", inverse="monster_sites"))

Only direct keys are declared. Composite references (a key that must also
agree with another field) and prefixed or parsed keys stay with the existing
per-registry validators and are never declared here.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

#: The ``dataclasses.field`` metadata key a declaration lives under.
REF_METADATA_KEY = "registry_ref"


@dataclass(frozen=True)
class RefSpec:
    """One declared reference: its target registry and the inverse name.

    ``inverse`` is the name under which a target entry lists the entries that
    reference it through this declaration. ``many`` fields hold a tuple, list
    or frozenset of keys; a ``nullable`` single field may hold ``None``.
    """

    registry: str
    inverse: str
    many: bool = False
    nullable: bool = False


def ref(registry: str, *, inverse: str, nullable: bool = False) -> Mapping[str, Any]:
    """Field metadata declaring that the field holds one key of ``registry``."""
    return MappingProxyType(
        {REF_METADATA_KEY: RefSpec(registry=registry, inverse=inverse, nullable=nullable)}
    )


def ref_many(registry: str, *, inverse: str) -> Mapping[str, Any]:
    """Field metadata declaring that the field holds a collection of keys."""
    return MappingProxyType(
        {REF_METADATA_KEY: RefSpec(registry=registry, inverse=inverse, many=True)}
    )


def ref_spec_of(field: dataclasses.Field) -> RefSpec | None:
    """The declaration on one dataclass field, or ``None``."""
    spec = field.metadata.get(REF_METADATA_KEY)
    return spec if isinstance(spec, RefSpec) else None


__all__ = ["REF_METADATA_KEY", "RefSpec", "ref", "ref_many", "ref_spec_of"]
