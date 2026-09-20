"""The player-preset bound and the frozen card dataclasses.

Holds the shared imports, the persona prose-field constant, and the six
frozen dataclasses (``PresetIdentity``, ``PresetAppearance``,
``PresetPersona``, ``PresetSexualBaseline``, ``StartingCompanion``,
``PlayerPreset``) moved verbatim from the single-module history; the
``data_*`` modules and ``validation`` build on this shared surface.
"""

from dataclasses import KW_ONLY, asdict, dataclass, fields
from math import isfinite
from typing import Any

from world.art.fallback_keys import validate_fallback_key
from world.lore.elements import ELEMENT_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.lore.sex import SEX_VALUES
from world.lore.sexual_vocab import (
    AROUSAL_LEVELS,
    BODY_PARTS,
    CLIMAX_PHASE_LEVELS,
    EXPOSURE_LEVELS,
    GENERIC_BODY_PART,
    SENSITIVITY_LEVELS,
    SHAME_LEVELS,
    WETNESS_LEVELS,
)
from world.lore.starting_kits import validate_wearable_loadout
from world.skills.registry import SKILL_REGISTRY, SkillKind

# The persona prose values the lore-side validator requires to be strings; the
# identity layers and appearance sub-keys are checked through their own
# dataclass field sets.
_PERSONA_PROSE_FIELDS = ("personality", "life_story", "habit", "background")


@dataclass(frozen=True)
class PresetIdentity:
    """The two identity layers PersonaStore renders (公開身分／隱秘身分)."""

    public: str = ""
    hidden: str = ""


@dataclass(frozen=True)
class PresetAppearance:
    """The seven appearance sub-keys declared in persona.py::_SUBKEY_ORDER."""

    height: str = ""
    weight: str = ""
    measurement: str = ""
    style: str = ""
    overview: str = ""
    attire: str = ""
    feature: str = ""


@dataclass(frozen=True)
class PresetPersona:
    """One preset's authored persona, in import-card record shape.

    Every value is optional and defaults to empty so a card can be authored
    incrementally; mutable containers are tuples of pairs to keep the registry
    immutable, and ``to_record()`` is the single place that expands them.
    """

    identity: PresetIdentity = PresetIdentity()
    personality: str = ""
    life_story: str = ""
    habit: str = ""
    appearance: PresetAppearance = PresetAppearance()
    social_connection: tuple[tuple[str, str], ...] = ()  # name -> relationship
    background: str = ""

    def to_record(self) -> dict[str, Any]:
        """Return the storage shape written to ``character.db.persona``.

        All six ``PERSONA_IMPORT_CARD_KEYS`` are always present (``""`` for
        unauthored prose, ``{}`` for unauthored structured keys), matching what
        custom activation and ``world.rules.persona_edit`` already produce; an
        empty ``identity`` layer is dropped from the identity subtree, empty
        appearance sub-keys are dropped, and ``background`` appears only when
        non-empty. ``social_connection`` stores the flat name -> relationship
        mapping (the one-level shape PersonaStore renders as
        ``名字：關係`` lines; the nested import-card form is its general case).
        The literal key set below mirrors
        ``world.rules.character_creation.PERSONA_IMPORT_CARD_KEYS``; lore must
        not import rules, and a rules-side test
        (``world/rules/tests/test_persona.py``) pins the two in lock step.
        """
        identity: dict[str, str] = {}
        if self.identity.public:
            identity["public"] = self.identity.public
        if self.identity.hidden:
            identity["hidden"] = self.identity.hidden
        appearance = {
            sub_key: value
            for sub_key, value in asdict(self.appearance).items()
            if value
        }
        record: dict[str, Any] = {
            "identity": identity,
            "personality": self.personality,
            "life_story": self.life_story,
            "habit": self.habit,
            "appearance": appearance,
            "social_connection": dict(self.social_connection),
        }
        if self.background:
            record["background"] = self.background
        return record


@dataclass(frozen=True)
class PresetSexualBaseline:
    """One preset's authored sexual baseline, in import-card record shape.

    Mirrors the import card's ``sexual_baseline`` object: ``arousal``,
    ``virgin``, and ``sensitivity`` are required; ``wetness``, ``shame``,
    ``exposure``, and ``climax_phase`` are optional, each empty value
    omitted from the record so ``SexualState``'s existing "default the
    omitted field to its vocabulary's lowest level" construction rule
    applies unchanged. ``sensitivity`` is a tuple of ``(body_part, level)``
    pairs so the registry stays immutable; ``to_record()`` expands it.
    """

    arousal: str
    virgin: bool
    sensitivity: tuple[tuple[str, str], ...]
    wetness: str = ""
    shame: str = ""
    exposure: str = ""
    climax_phase: str = ""

    def to_record(self) -> dict[str, Any]:
        """Return the storage shape written to ``character.db.sexual``.

        The three required keys are always present and ``sensitivity``
        becomes the flat body-part -> level mapping ``SexualState`` seeds
        from; each empty optional level is omitted rather than written as
        a literal, and ``climax_today`` / ``experience_types`` are never
        written because the builder already floors them at construction.
        """
        record: dict[str, Any] = {
            "arousal": self.arousal,
            "virgin": self.virgin,
            "sensitivity": dict(self.sensitivity),
        }
        for field in ("wetness", "shame", "exposure", "climax_phase"):
            value = getattr(self, field)
            if value:
                record[field] = value
        return record


@dataclass(frozen=True)
class StartingCompanion:
    """One preset's declared NPC companion, keyed by the partner's own card.

    ``preset_key`` names the companion's OWN ``PLAYER_PRESET_REGISTRY`` entry,
    so the companion's stats, skills, items, persona, and identity always come
    from the same card a player could have chosen -- never a second authored
    copy. ``affinity`` is the value the activation binding seeds into the
    relationship record (its numeric bounds derive from ``world.rules``
    constants and are swept rules-side, because lore must not import rules);
    ``relationship`` is the label written into the built companion's persona
    ``social_connection`` under the owning player's name.
    """

    preset_key: str
    affinity: int
    relationship: str


@dataclass(frozen=True)
class PlayerPreset:
    """A complete player-owned identity, raw stat allocation, and skill kit.

    ``allocations`` covers all seven allocatable axes (the three gauges and the
    four statics); the ``magic_power`` entry fixes the preset's starting magic
    power as a literal (growth-redesign D-A5 deleted the magic sampler).
    """

    key: str
    display_name: str
    age: int
    apparent_age: int
    race: str
    subrace: str
    allocations: tuple[tuple[str, int], ...]
    emphasis: str
    active_skills: tuple[str, ...] = ()
    passive_skills: tuple[str, ...] = ()
    affinity_elements: tuple[str, ...] = ()
    starting_items: tuple[tuple[str, int], ...] = ()
    # KW_ONLY from the first preset-parity field onward (field-parity design
    # 3.2): ``sex`` is a required keyword argument, so a new card that omits
    # it fails at construction instead of silently inheriting DEFAULT_SEX.
    # Removing the positional ``background`` slot shifted the former trailing
    # positional arguments, so every shipped card now passes the skill,
    # affinity, and persona fields by keyword.
    _: KW_ONLY
    sex: str
    # Declared starting practice XP as ``(skill_key, xp)`` pairs
    # (preset-lineage-and-proficiency). A declared entry always wins over the
    # activation auto-seed, even when it leaves a prerequisite edge unmet --
    # the same precedence an explicit import-record ``skill_proficiency``
    # entry has. An entry may name a key outside the preset's closed kit; it
    # is then persisted verbatim exactly as the import path persists one.
    skill_proficiency: tuple[tuple[str, float], ...] = ()
    # Which of the declared starting items are WORN at activation
    # (preset-starting-equipment). Every key SHALL be a subset of
    # ``starting_items`` (the pack stays the single source of what the
    # character owns) and name registry equipment; activation applies each
    # through ``world/rules/equipment.py::toggle_equipment``, the sole
    # equipment writer. The empty default keeps every shipped card's
    # observable starting state unchanged until an author fills the field.
    starting_equipment: tuple[str, ...] = ()
    persona: PresetPersona = PresetPersona()
    # The display-only disguise layer (preset-disguise-and-sexual-baseline)
    # as ``(axis_key, value)`` pairs. Keys are NOT whitelisted:
    # ``CHARACTER_SCHEMA_V1`` constrains the field only to integer values
    # (its subset-of-stats rule is an import-path semantic check the preset
    # path cannot mirror, because presets declare allocations, not absolute
    # stats), and display values never reach combat or resolution. The empty
    # default writes ``None``, which every reader treats as absent.
    disguised_stats: tuple[tuple[str, int], ...] = ()
    # The authored sexual baseline seeding ``entity.db.sexual`` (same
    # change). ``None`` writes nothing, so ``SexualState`` keeps applying
    # ``_generic_default_baseline()`` lazily exactly as before.
    sexual_baseline: PresetSexualBaseline | None = None
    # The declared NPC companions (starting-companions). Each entry names the
    # partner's own preset card, the affinity the activation binding seeds,
    # and the persona relationship label. The empty default keeps every
    # shipped card's observable starting state unchanged until an author fills
    # the field. Presence/self/duplicate shape is validated lore-side at load;
    # the bounds reading rules constants (companion count against
    # ``PARTY_MAX_COMPANIONS``, affinity against ``NATURAL_CAP``) are swept at
    # ``world/rules/starting_companions.py`` import time.
    starting_companions: tuple[StartingCompanion, ...] = ()
    # The OPTIONAL built-in gallery fallback key (gallery-builtin-fallbacks).
    # A preset MAY claim one key of the closed vocabulary outright, which
    # wins over the sex/age band rule for every character activated from it.
    # The unset default keeps every shipped card valid without one. The key
    # vocabulary lives in the dependency-neutral ``world.art.fallback_keys``
    # -- the only ``world.art`` surface lore may import -- and is checked at
    # registry construction below so a typo fails loudly at import.
    fallback_key: str | None = None

    def allocation_dict(self) -> dict[str, int]:
        """Return a mutable copy suitable for rules validation."""
        return dict(self.allocations)

    def skill_lists(self) -> dict[str, list[str]]:
        """Return the storage shape for the character ``skills`` attribute."""
        return {"active": list(self.active_skills), "passive": list(self.passive_skills)}

    def inventory_list(self) -> list[str]:
        """Return the flat repeated-key inventory the activation hands out."""
        return [
            item_key
            for item_key, quantity in self.starting_items
            for _ in range(quantity)
        ]
