"""Pure parser and checker for the keyed bestiary documentation contract.

The published bestiary (`docs/lore/bestiary.md`) carries the reader-facing
prose; this module owns the machine-readable part of it. Each current species
section encloses one fenced ``bestiary`` block naming the species key, the
parent species key, the default variant key, every owned variant with its
kit-backed executable status, the public registry fields the section
documents, and the species' own status. Everything after the
``<!-- bestiary-current-end -->`` boundary is historical appendix text and
never satisfies current coverage.

Both halves are pure: :func:`parse_bestiary_document` turns markdown text into
sections, and :func:`check_bestiary_documentation` compares those sections with
registry rows and their published projections. Neither reads a file, opens a
database, or pins a prose sentence, so rewording valid prose can never fail a
relationship check.
"""

import yaml
from dataclasses import dataclass

from world.lore.monster_species import published_species_view, published_variant_view

FENCE = "bestiary"
CURRENT_END_MARKER = "<!-- bestiary-current-end -->"
SECTION_HEADING = "###"
#: The two declared executable statuses: a variant either delivers an authored
#: kit or stays narrative-only.
DELIVERED = "delivered"
NARRATIVE = "narrative"
#: The registry fields a current section has to name, per documented face. Only
#: names, never values: the prose itself is the section body, which stays
#: freely editable. Deliberately a tuple rather than a module-level mapping, so
#: this checker is never mistaken for a catalog-data module by the test-data
#: universe derivation.
REQUIRED_FIELDS_BY_FACE = (
    ("species", ("display_name_zh", "published_description_zh", "published_ecology_zh")),
    ("variant", ("display_name_zh", "description_zh")),
)
BLOCK_REQUIRED_KEYS = (
    "species",
    "parent-species",
    "default-variant",
    "variants",
    "public-fields",
    "status",
)


@dataclass(frozen=True)
class BestiarySection:
    """One ``###`` section of the document, with its parsed metadata block."""

    title: str
    body: str
    metadata: dict | None
    extra_blocks: bool
    is_current: bool


@dataclass(frozen=True)
class BestiaryDocument:
    """The parsed document, split at the historical boundary."""

    current: tuple[BestiarySection, ...]
    historical: tuple[BestiarySection, ...]


def _split_sections(lines: list[str], *, is_current: bool) -> list[BestiarySection]:
    sections: list[BestiarySection] = []
    title: str | None = None
    body: list[str] = []

    def flush() -> None:
        if title is None:
            return
        metadata, extra_blocks = _extract_metadata(body)
        sections.append(
            BestiarySection(
                title=title,
                body=_strip_blocks(body),
                metadata=metadata,
                extra_blocks=extra_blocks,
                is_current=is_current,
            )
        )

    for line in lines:
        if line.startswith(f"{SECTION_HEADING} "):
            flush()
            title = line[len(SECTION_HEADING) + 1:].strip()
            body = []
            continue
        if title is not None:
            body.append(line)
    flush()
    return [section for section in sections if section.body or section.metadata]


def _extract_metadata(lines: list[str]) -> tuple[dict | None, bool]:
    """The first fenced ``bestiary`` block of one section, and whether the
    section carried a second one (a second claim is always a fault)."""
    blocks: list[list[str]] = []
    inside = False
    kind = ""
    collected: list[str] = []
    for line in lines:
        if line.startswith("```"):
            if inside:
                if kind == FENCE:
                    blocks.append(collected)
                inside = False
                kind = ""
                collected = []
            else:
                inside = True
                kind = line.strip("`").strip()
                collected = []
            continue
        if inside:
            collected.append(line)
    if inside and kind == FENCE:  # an unterminated fence is still a claim
        blocks.append(collected)
    if not blocks:
        return None, False
    try:
        parsed = yaml.safe_load("\n".join(blocks[0])) if blocks[0] else None
    except yaml.YAMLError:
        parsed = None
    if not isinstance(parsed, dict):
        return None, len(blocks) > 1
    return parsed, len(blocks) > 1


def _strip_blocks(lines: list[str]) -> str:
    kept: list[str] = []
    inside = False
    for line in lines:
        if line.startswith("```"):
            inside = not inside
            continue
        if not inside:
            kept.append(line)
    return "\n".join(kept).strip()


def parse_bestiary_document(text: str) -> BestiaryDocument:
    """Split one bestiary document into its current and historical sections."""
    lines = text.splitlines()
    if CURRENT_END_MARKER in lines:
        index = lines.index(CURRENT_END_MARKER)
        current_lines, historical_lines = lines[:index], lines[index + 1:]
    else:
        current_lines, historical_lines = lines, []
    return BestiaryDocument(
        current=tuple(_split_sections(current_lines, is_current=True)),
        historical=tuple(_split_sections(historical_lines, is_current=False)),
    )


def _status_of_variant(variant) -> str:
    """The declared kit-backed executable status of one variant row."""
    return DELIVERED if (variant.active_skill_keys or variant.passive_skill_keys) else NARRATIVE


def _public_field_surface(species, variants) -> set[str]:
    """The documented-authority field names: the published projections' keys."""
    surface = set(published_species_view(species))
    for variant in variants:
        surface |= set(published_variant_view(variant))
    return surface


def _required_field_names(species, variants) -> set[str]:
    required: set[str] = set()
    for face, fields in REQUIRED_FIELDS_BY_FACE:
        rows = (species,) if face == "species" else tuple(variants)
        for row in rows:
            required |= {
                field for field in fields if getattr(row, field, "")
            }
    return required


def check_bestiary_documentation(
    species_rows,
    variant_rows,
    document: BestiaryDocument,
) -> tuple[str, ...]:
    """Return one problem string per broken keyed relationship (empty when valid).

    Every problem names the key and the relationship that failed, so a missing,
    duplicated, orphaned, mis-parented, field-incomplete, private-field or
    status-mismatched section is diagnosable from the message alone.
    """
    problems: list[str] = []
    documented: dict[str, dict] = {}
    variant_documents: dict[str, str] = {}

    for section in document.current:
        if section.extra_blocks:
            problems.append(
                f"{section.title}: carries more than one {FENCE!r} metadata block"
            )
        if section.metadata is None:
            problems.append(
                f"{section.title}: current section carries no parseable "
                f"{FENCE!r} metadata block"
            )
            continue
        metadata = section.metadata
        missing = [key for key in BLOCK_REQUIRED_KEYS if key not in metadata]
        if missing:
            problems.append(
                f"{section.title}: metadata block is missing {sorted(missing)}"
            )
            continue
        species_key = metadata["species"]
        if not isinstance(species_key, str):
            problems.append(f"{section.title}: species key is not a string")
            continue
        if species_key in documented:
            problems.append(f"{species_key}: documented by more than one section")
            continue
        documented[species_key] = metadata
        if not section.body:
            problems.append(f"{species_key}: current section carries no prose body")
        variants = metadata["variants"] or []
        if not isinstance(variants, list) or not variants:
            problems.append(f"{species_key}: metadata block names no variant")
            continue
        for entry in variants:
            if not isinstance(entry, dict) or "key" not in entry:
                problems.append(f"{species_key}: variant entry is not a keyed mapping")
                continue
            variant_key = entry["key"]
            if variant_key in variant_documents:
                problems.append(
                    f"{variant_key}: documented twice "
                    f"(also under {variant_documents[variant_key]})"
                )
                continue
            variant_documents[variant_key] = species_key

    for key, metadata in documented.items():
        species = species_rows.get(key)
        if species is None:
            problems.append(f"{key}: documented species is not in the registry")
            continue
        parent = metadata["parent-species"]
        if parent != key:
            problems.append(
                f"{key}: parent-species {parent!r} is not the owning species"
            )
        owned = {
            variant_key: variant
            for variant_key, variant in variant_rows.items()
            if variant.species_key == key
        }
        if not owned:
            problems.append(f"{key}: registry owns no variant")
            continue
        listed = [
            entry["key"] for entry in metadata["variants"] if isinstance(entry, dict)
        ]
        for variant_key in sorted(owned):
            if variant_key not in listed:
                problems.append(
                    f"{variant_key}: owned by {key} but missing from its section"
                )
        for variant_key in listed:
            variant = owned.get(variant_key)
            if variant is None:
                problems.append(
                    f"{variant_key}: documented under {key} but not owned by it"
                )
                continue
            entry = next(
                entry for entry in metadata["variants"] if entry["key"] == variant_key
            )
            status = entry.get("status")
            if status not in (DELIVERED, NARRATIVE):
                problems.append(f"{variant_key}: unparseable status {status!r}")
            elif status != _status_of_variant(variant):
                problems.append(
                    f"{variant_key}: status {status!r} contradicts its declared kit"
                )
        default = metadata["default-variant"]
        if default not in listed:
            problems.append(
                f"{key}: default variant {default!r} is not documented as an owned variant"
            )
        elif default != species.default_variant_key:
            problems.append(
                f"{key}: default variant {default!r} is not the registry default"
            )
        elif not getattr(owned.get(default), "ordinary_variant", False):
            problems.append(
                f"{key}: default variant {default!r} is not an ordinary variant"
            )
        species_status = metadata["status"]
        expected_status = (
            DELIVERED
            if any(_status_of_variant(variant) == DELIVERED for variant in owned.values())
            else NARRATIVE
        )
        if species_status != expected_status:
            problems.append(
                f"{key}: status {species_status!r} contradicts its declared kits"
            )
        fields = metadata["public-fields"] or []
        if not isinstance(fields, list) or not fields:
            problems.append(f"{key}: metadata block names no public field")
            continue
        surface = _public_field_surface(species, owned.values())
        for field in fields:
            if field not in surface:
                problems.append(
                    f"{key}: {field!r} is not a published registry field"
                )
        required = _required_field_names(species, owned.values())
        for field in sorted(required - set(fields)):
            problems.append(f"{key}: public field {field!r} is not documented")

    for key in sorted(set(species_rows) - set(documented)):
        problems.append(f"{key}: shipped species is not documented by any current section")

    for section in document.historical:
        if section.metadata is not None:
            problems.append(
                f"{section.title}: historical section carries current-coverage metadata"
            )

    return tuple(problems)
