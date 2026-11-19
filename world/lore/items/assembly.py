"""Item catalog assembly: the single authored ``content/items/`` source.

``content/items/catalog.yaml`` is the only entry point. It names an ordered
list of slice files (``schema_version: 1`` plus ``files``); each slice authors
one ``items`` list of typed rows. File order is the presentation order and row
order inside a file is preserved, so the loaded ``ITEM_REGISTRY`` keeps the
order every consumer observes (inventory breakdown, data lint, presentation).

This module is a data-only reader: it imports the item vocabulary and PyYAML,
never ``world.rules``. A usable row authors its ordered effect entries under
``use_mechanics.effects`` and an equipment row authors its dedicated
``equipment_effects`` mapping on the row itself; both stay raw inputs here and
``world/rules/item_effects.py`` / ``world/rules/equipment_effects.py`` attach
their validated meaning after lore has loaded. The effect modules never reread
item rows independently of these definitions.

Validation is fail-loud and names the source file, the item key, and the
offending field: unknown fields, duplicate keys (mapping keys or item keys),
unreadable/undeclared files, wrong scalar types, non-data YAML constructs, and
an equipment row without its effect mapping (``{}`` is the explicit
no-effects declaration) are all rejected before any candidate is published.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

from world.lore.items.vocab import (
    ItemDefinition,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
    ItemUseMechanics,
    LiturgicalRole,
)
from world.skills.equipment import EquipmentSlot

#: Repository root, used to report repository-relative source paths.
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]

#: The one catalog directory and its manifest name.
CATALOG_DIRECTORY = REPOSITORY_ROOT / "content" / "items"
CATALOG_FILENAME = "catalog.yaml"

#: The only accepted manifest schema version.
SCHEMA_VERSION = 1

#: The stable item-key grammar. A colon would break the existing
#: ``buff_key:item_key`` attachment identifier, hence the closed shape.
ITEM_KEY_PATTERN = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*\Z")

_ROW_REQUIRED_FIELDS = frozenset(
    {"key", "display_name_zh", "price_table_key", "sellable", "presentation"}
)
_ROW_OPTIONAL_FIELDS = frozenset(
    {
        "guild_property",
        "liturgical_role",
        "use_mechanics",
        "equipment_slot",
        "equipment_effects",
    }
)
_PRESENTATION_FIELDS = frozenset({"kind", "icon_key", "rarity", "summary_zh"})
_USE_MECHANICS_FIELDS = frozenset({"consumable", "combat_allowed", "effects"})


class ItemCatalogError(ValueError):
    """The authored item catalog is malformed, missing, or contradictory."""


@dataclass(frozen=True)
class ItemCatalog:
    """One loaded catalogue candidate: definitions, provenance, and raw effects."""

    definitions: Mapping[str, ItemDefinition]
    sources: Mapping[str, str]
    use_effect_inputs: Mapping[str, tuple[dict[str, Any], ...]]
    equipment_effect_inputs: Mapping[str, dict[str, Any]]


def _display_path(path: Path) -> str:
    """The repository-relative path when it resolves there, else the real path."""
    try:
        return path.resolve().relative_to(REPOSITORY_ROOT).as_posix()
    except (ValueError, OSError):
        return str(path)


def _resolve_contained(path: Path, root: Path, where: str) -> Path:
    """Resolve ``path`` and require it to stay inside the catalog directory.

    ``Path.is_file()`` follows symlinks, so a declared slice could otherwise
    point at an external file and break the single-source boundary. The
    resolved target must live under the resolved catalog root.
    """
    try:
        resolved = path.resolve()
        resolved.relative_to(root.resolve())
    except (OSError, ValueError):
        raise ItemCatalogError(
            f"{where}: resolves outside the item catalog directory"
        ) from None
    return resolved


def _unique_key_loader(source: str):
    """A SafeLoader that refuses duplicate mapping keys, naming the source."""

    class _UniqueKeyLoader(yaml.SafeLoader):
        def construct_mapping(self, node: Any, deep: bool = False) -> Any:
            seen: set[Any] = set()
            for key_node, _ in node.value:
                key = self.construct_object(key_node, deep=deep)
                if key in seen:
                    raise ItemCatalogError(
                        f"{source}: duplicate YAML mapping key {key!r} at line "
                        f"{key_node.start_mark.line + 1}"
                    )
                seen.add(key)
            return super().construct_mapping(node, deep=deep)

    return _UniqueKeyLoader


def _read_yaml(path: Path) -> Any:
    source = _display_path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ItemCatalogError(f"{source}: cannot be read ({error})") from None
    try:
        return yaml.load(text, Loader=_unique_key_loader(source))
    except ItemCatalogError:
        raise
    except yaml.YAMLError as error:
        raise ItemCatalogError(f"{source}: malformed YAML ({error})") from None


def _require_mapping(value: Any, where: str) -> Mapping[Any, Any]:
    if not isinstance(value, Mapping):
        raise ItemCatalogError(f"{where} must be a mapping, got {value!r}")
    return value


def _require_fields(
    mapping: Mapping[Any, Any], required: frozenset[str], allowed: frozenset[str], where: str
) -> None:
    unknown = sorted({str(key) for key in mapping} - allowed)
    if unknown:
        raise ItemCatalogError(f"{where} contains unknown fields: {unknown}")
    missing = sorted(required - set(mapping))
    if missing:
        raise ItemCatalogError(f"{where} is missing required fields: {missing}")


def _require_string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ItemCatalogError(f"{where} must be a non-empty string, got {value!r}")
    return value


def _require_bool(value: Any, where: str) -> bool:
    if not isinstance(value, bool):
        raise ItemCatalogError(f"{where} must be a boolean, got {value!r}")
    return value


def _require_enum(vocabulary: Any, value: Any, where: str) -> Any:
    try:
        return vocabulary(value)
    except (TypeError, ValueError):
        members = ", ".join(member.value for member in vocabulary)
        raise ItemCatalogError(
            f"{where} must be one of {members}, got {value!r}"
        ) from None


def _parse_presentation(value: Any, where: str) -> ItemPresentation:
    mapping = _require_mapping(value, where)
    _require_fields(mapping, _PRESENTATION_FIELDS, _PRESENTATION_FIELDS, where)
    return ItemPresentation(
        kind=_require_enum(ItemKind, mapping["kind"], f"{where}.kind"),
        icon_key=_require_enum(ItemIconKey, mapping["icon_key"], f"{where}.icon_key"),
        rarity=_require_enum(ItemRarity, mapping["rarity"], f"{where}.rarity"),
        summary_zh=_require_string(mapping["summary_zh"], f"{where}.summary_zh"),
    )


def _parse_use_mechanics(value: Any, where: str) -> tuple[ItemUseMechanics, list[dict[str, Any]]]:
    mapping = _require_mapping(value, where)
    _require_fields(mapping, _USE_MECHANICS_FIELDS, _USE_MECHANICS_FIELDS, where)
    mechanics = ItemUseMechanics(
        consumable=_require_bool(mapping["consumable"], f"{where}.consumable"),
        combat_allowed=_require_bool(
            mapping["combat_allowed"], f"{where}.combat_allowed"
        ),
    )
    effects = mapping["effects"]
    if not isinstance(effects, list):
        raise ItemCatalogError(f"{where}.effects must be a list, got {effects!r}")
    raw: list[dict[str, Any]] = []
    for position, entry in enumerate(effects, start=1):
        entry_where = f"{where}.effects[{position}]"
        entry_mapping = _require_mapping(entry, entry_where)
        raw.append(dict(entry_mapping))
    return mechanics, raw


def _parse_equipment_effects(value: Any, where: str) -> dict[str, Any]:
    mapping = _require_mapping(value, where)
    return dict(mapping)


def _parse_row(row: Any, where: str) -> tuple[ItemDefinition, list[dict[str, Any]] | None, dict[str, Any] | None]:
    mapping = _require_mapping(row, where)
    _require_fields(mapping, _ROW_REQUIRED_FIELDS, _ROW_REQUIRED_FIELDS | _ROW_OPTIONAL_FIELDS, where)
    raw_key = mapping["key"]
    key = _require_string(raw_key, f"{where}.key")
    if not ITEM_KEY_PATTERN.match(key):
        raise ItemCatalogError(
            f"{where}.key {key!r} must match [a-z][a-z0-9]*(?:_[a-z0-9]+)*"
        )

    kwargs: dict[str, Any] = {
        "key": key,
        "display_name_zh": _require_string(
            mapping["display_name_zh"], f"{where}.display_name_zh"
        ),
        "price_table_key": _require_string(
            mapping["price_table_key"], f"{where}.price_table_key"
        ),
        "sellable": _require_bool(mapping["sellable"], f"{where}.sellable"),
        "presentation": _parse_presentation(
            mapping["presentation"], f"{where}.presentation"
        ),
    }

    if "guild_property" in mapping:
        kwargs["guild_property"] = _require_bool(
            mapping["guild_property"], f"{where}.guild_property"
        )
    if "liturgical_role" in mapping:
        kwargs["liturgical_role"] = _require_enum(
            LiturgicalRole, mapping["liturgical_role"], f"{where}.liturgical_role"
        )

    use_effect_inputs: list[dict[str, Any]] | None = None
    equipment_effect_inputs: dict[str, Any] | None = None

    if "use_mechanics" in mapping:
        mechanics, use_effect_inputs = _parse_use_mechanics(
            mapping["use_mechanics"], f"{where}.use_mechanics"
        )
        kwargs["use_mechanics"] = mechanics
    if "equipment_slot" in mapping:
        kwargs["equipment_slot"] = _require_enum(
            EquipmentSlot, mapping["equipment_slot"], f"{where}.equipment_slot"
        )
    if "equipment_effects" in mapping:
        equipment_effect_inputs = _parse_equipment_effects(
            mapping["equipment_effects"], f"{where}.equipment_effects"
        )

    has_slot = "equipment_slot" in mapping
    has_use = "use_mechanics" in mapping
    if has_use and has_slot:
        raise ItemCatalogError(
            f"{where} ({key!r}) declares both use_mechanics and equipment_slot; "
            "the mechanics are mutually exclusive"
        )
    if has_slot and "equipment_effects" not in mapping:
        raise ItemCatalogError(
            f"{where} ({key!r}) declares an equipment slot without "
            "equipment_effects; author {} for effectless equipment"
        )
    if not has_slot and "equipment_effects" in mapping:
        raise ItemCatalogError(
            f"{where} ({key!r}) declares equipment_effects without an "
            "equipment slot; only equipment binds effects"
        )

    try:
        definition = ItemDefinition(**kwargs)
    except ValueError as error:
        raise ItemCatalogError(f"{where} ({key!r}): {error}") from None
    return definition, use_effect_inputs, equipment_effect_inputs


def load_item_catalog(directory: Path | None = None) -> ItemCatalog:
    """Load and validate one catalogue candidate rooted at ``directory``.

    Defaults to the shipped ``content/items/`` directory; tests pass a
    temporary copy to exercise authoring errors without touching shipped
    files. Nothing is published until every declared document validates.
    """
    root = Path(directory) if directory is not None else CATALOG_DIRECTORY
    root = root.resolve()
    manifest_path = root / CATALOG_FILENAME
    if not root.is_dir() or not manifest_path.is_file():
        raise ItemCatalogError(f"{_display_path(manifest_path)}: catalog manifest is missing")
    _resolve_contained(manifest_path, root, _display_path(manifest_path))

    manifest = _require_mapping(
        _read_yaml(manifest_path), _display_path(manifest_path)
    )
    _require_fields(
        manifest,
        frozenset({"schema_version", "files"}),
        frozenset({"schema_version", "files"}),
        _display_path(manifest_path),
    )
    version = manifest["schema_version"]
    if isinstance(version, bool) or not isinstance(version, int) or version != SCHEMA_VERSION:
        raise ItemCatalogError(
            f"{_display_path(manifest_path)}.schema_version must be the integer "
            f"{SCHEMA_VERSION}, got {version!r}"
        )
    files = manifest["files"]
    if not isinstance(files, list) or not files:
        raise ItemCatalogError(
            f"{_display_path(manifest_path)}.files must be a non-empty list"
        )
    names: list[str] = []
    for position, name in enumerate(files, start=1):
        where = f"{_display_path(manifest_path)}.files[{position}]"
        name = _require_string(name, where)
        if Path(name).name != name or name == CATALOG_FILENAME or not name.endswith(".yaml"):
            raise ItemCatalogError(
                f"{where} {name!r} must be a distinct declared .yaml basename "
                f"other than {CATALOG_FILENAME}"
            )
        if name in names:
            raise ItemCatalogError(f"{where} repeats the declared file {name!r}")
        names.append(name)

    present = {path.name for path in root.glob("*.yaml")} - {CATALOG_FILENAME}
    undeclared = sorted(present - set(names))
    if undeclared:
        raise ItemCatalogError(
            f"{_display_path(root)}: undeclared item catalog files: {undeclared}"
        )
    missing = sorted(set(names) - present)
    if missing:
        raise ItemCatalogError(
            f"{_display_path(root)}: declared item catalog files are missing: {missing}"
        )

    definitions: dict[str, ItemDefinition] = {}
    sources: dict[str, str] = {}
    use_inputs: dict[str, tuple[dict[str, Any], ...]] = {}
    equipment_inputs: dict[str, dict[str, Any]] = {}

    for name in names:
        path = root / name
        if not path.is_file():
            raise ItemCatalogError(f"{_display_path(path)}: not a readable regular file")
        _resolve_contained(path, root, _display_path(path))
        source = _display_path(path)
        document = _require_mapping(_read_yaml(path), source)
        _require_fields(document, frozenset({"items"}), frozenset({"items"}), source)
        rows = document["items"]
        if not isinstance(rows, list):
            raise ItemCatalogError(f"{source}.items must be a list, got {rows!r}")
        for position, row in enumerate(rows, start=1):
            where = f"{source}.items[{position}]"
            definition, use_effect_inputs, equipment_effect_inputs = _parse_row(row, where)
            key = definition.key
            if key in definitions:
                raise ItemCatalogError(
                    f"{where} ({key!r}) repeats the item key declared in "
                    f"{sources[key]}"
                )
            definitions[key] = definition
            sources[key] = source
            if use_effect_inputs is not None:
                use_inputs[key] = tuple(use_effect_inputs)
            if equipment_effect_inputs is not None:
                equipment_inputs[key] = equipment_effect_inputs

    return ItemCatalog(
        definitions=MappingProxyType(definitions),
        sources=MappingProxyType(sources),
        use_effect_inputs=MappingProxyType(use_inputs),
        equipment_effect_inputs=MappingProxyType(equipment_inputs),
    )


#: The loaded production candidate. The registries below are views over it and
#: keep their historical identities: ``ITEM_REGISTRY`` is a mutable dict (the
#: synthetic kit swaps it in place) published in authored order.
ITEM_CATALOG = load_item_catalog()
ITEM_REGISTRY: dict[str, ItemDefinition] = {
    key: definition for key, definition in ITEM_CATALOG.definitions.items()
}
ITEM_SOURCES: dict[str, str] = dict(ITEM_CATALOG.sources)
ITEM_USE_EFFECT_INPUTS: dict[str, tuple[dict[str, Any], ...]] = dict(
    ITEM_CATALOG.use_effect_inputs
)
ITEM_EQUIPMENT_EFFECT_INPUTS: dict[str, dict[str, Any]] = dict(
    ITEM_CATALOG.equipment_effect_inputs
)
