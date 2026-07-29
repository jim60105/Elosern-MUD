## Context

This is roadmap item #5 (design doc §11), depending on change 3 (`entity-traits`, which provides
`LivingEntity`, the `skills`/`equipment` placeholder seam attributes, `race_floor()`, and the
base-value trait boundary D-7). No code exists yet for this change's scope — `world/skills/` does
not exist as even an empty stub; design doc §3.2 forward-declares the package but no earlier change
created it.

Two artifacts already depend on this change's exact shape before it exists:

1. **Change 4 (`import-contract`) forward-declared the module path and symbol this change must
   satisfy**: `world.skills.registry.SKILL_REGISTRY`, a `Mapping[str, Any]` keyed by skill key. Its
   `_check_skills()` currently degrades to a WARNING and prints a "DEGRADED VALIDATION" banner on
   every CLI run, specifically because this module does not exist. A self-arming test
   (`world/imports/tests/test_skill_registry_self_arming.py`) sits `skipped` — not passed, not
   failed — until `world.skills.registry` is genuinely importable, at which point it starts
   asserting that an unknown skill key is REJECTED. **This design must land at exactly that path with
   a genuinely enforcing registry**, or change 4's own test suite fails the moment someone runs it
   against this change's code — the self-arming mechanism does not tolerate a registry that exists
   but is empty or trivially satisfies every key.
2. **Change 3's D-7 established a boundary this change must operate under, not just respect on
   paper**: every value in `entity.traits` is a base value; skill multipliers (×10/×100/×1000, per
   the source cards' `88*1000` notation) are "applied at resolution time by whichever module computes
   effective combat power (change 5's skill-effect resolution and/or change 9's combat math)." This
   change is the first one to actually write that resolution-time computation, so it is also the
   first change where "never baked into `entity.traits`" becomes a testable, not just documented,
   property of running code.

The five sample character cards in `tmp/story_settings/character/` (gitignored, never committed, not
shippable game data per design doc §1's age gate) are read here only to inventory *what shapes* of
skill this system must express — stat multipliers, elemental mastery, direct spells, weapon arts, a
display-only disguise skill, a skill that partially confers another entity's skill, and a set of
passives including a per-character-unique one. None of their numeric or narrative content is
authoritative; `world_info.md` and design doc §5.1/§5.2 are.

## Goals / Non-Goals

**Goals:**
- `world/skills/registry.py`: `SkillKind`, `TargetSpec`, `SkillDef` (exactly design doc §5.2's seven
  fields), and `SKILL_REGISTRY` at the exact forward-declared path, seeded with a representative
  cross-category skill set (not an exhaustive catalogue of every skill on every card).
- `world/skills/handler.py`: `SkillHandler`, a facade over the raw dict change 4's loader already
  writes to `entity.skills`, with `effective_value()` as the **one and only place** a stat-multiplier
  skill's multiplier is applied — reading a base trait value and returning a derived, transient
  result, never writing back.
- A concrete, buildable data model and read-side computation for 統御術's partial-conferral
  mechanic (Violet's card: a ×10 grant from Elosia's ×100 身體強化) — the mechanic this task
  description calls "the most structurally awkward skill in the set."
- A structural guarantee — not just a docstring — that 狀態偽裝's effect resolution cannot violate
  decision D2: its effect-application code path touches `entity.db.disguised_stats` and nothing else.
- `world/skills/equipment.py`: equipment slots borrowing evadventure's wield-location *structure*
  (design doc §4: reference only) sized to what the sample cards actually show (single or dual
  weapons, one armor slot, a handful of accessories), plus inventory helper functions compatible with
  change 4's `entity.db.inventory` write pattern.
- A verification step confirming change 4's self-arming test transitions from skipped to
  passing — the acceptance criterion for the cross-change contract change 4 already wrote against
  this change's forward-declared path.

**Non-Goals:**
- No `ActionResolver`, targeting, resource-check pipeline, or effect-resolution engine — change 8's
  job. This change declares `TargetSpec`/`SkillKind` for change 8 to import and builds the read-side
  multiplier/conferral computation, but nothing in this change decides *when* a skill is cast, checks
  `mp`/`sp` cost against current pool, or validates a target. A skill in this change's registry is
  data plus a pure query function, never an executable action.
- No rulebook YAML engine or interpretation of arbitrary `effects: list[str]` IDs beyond the
  `stat_multiply:<trait>:<multiplier>` convention this change defines for its own multiplier
  resolution — change 6's job. Every other effect ID (`damage:fire:magic`, `movement:flight`,
  `passive_buff:defense_small`, etc.) is opaque data here, exactly as `persona` is opaque to change 4.
- No `BuffHandler`, duration tracking, or stacking — change 6's job. This change's stat-multiplier
  resolution is a stateless query (does the entity currently list this skill key as active?), not a
  timed effect with decay.
- No combat, damage, or overwhelm-threshold logic (changes 9–10) — this change only guarantees that
  whatever those changes build can call `SkillHandler.effective_value()` to get a multiplied number
  for one calculation.
- No 統御術 cast-time grant-creation path (an entity actually casting the skill on another entity
  during play) — declared as a seam for change 8. This change builds the data shape
  (`ConferredSkillGrant`) and the read-side fold-in computation only.
- No partial magic-growth-rate conferral (Elosia's 轉生特典 partial effect on Violet) — this is a
  learning-rate/progression concept, not a combat-stat multiplier, and has no obvious owning change
  yet (see Open Questions). Declared as an unresolved seam, not built.
- No sexual-state mechanics (change 7) — 性魔法主宰/神之秘法：性愛系統-type skills are registered as
  opaque `SkillDef` entries with `effects` IDs that change 7 will eventually interpret; this change
  does not simulate arousal or any sexual-state field.
- No item/loot definitions, crafting, weight/capacity limits, or shop pricing — inventory here is
  "a list of item-key strings," nothing more. `Monster.loot_table` (change 3's declared seam) is not
  populated by this change either — no roadmap item has explicitly claimed it yet.
- No backward-compatibility, migration, or deprecation handling — the project is unreleased with
  zero users, and `world/skills/` currently contains no code at all (not even an empty stub, since no
  earlier change created one).

## Decisions

### D-1. Package layout: `registry.py` / `handler.py` / `equipment.py`, matching design doc §3.2's
own parenthetical exactly.

```
world/skills/
├── __init__.py     re-exports SkillDef, SkillKind, TargetSpec, SKILL_REGISTRY, SkillHandler,
│                    EquipmentSlot, EquipmentHandler
├── registry.py      SkillKind, TargetSpec, SkillDef, SKILL_REGISTRY (seed data)
├── handler.py        SkillHandler, ConferredSkillGrant, effective_value(), the D2-compliant
│                     狀態偽裝 effect function
├── equipment.py       EquipmentSlot, EquipmentHandler, add_item/remove_item/list_items
└── tests/              one module per file above, plus a cross-change contract test
```

Design doc §3.2 spells out the package's contents in one line — "registry (SkillDef definitions) ·
handler · equipment" — which maps directly onto three modules rather than the one-module-per-
dataclass style change 2 used for `world/lore/`. Unlike `world/lore/`, this package's modules aren't
independent categories read by unrelated consumers; `handler.py` and `equipment.py` each depend on
`registry.py`'s types, so splitting further would buy nothing. No YAML file is added — the effect IDs
this change stores are opaque strings; `rulebook/` (change 6) is a separate directory design doc §3.2
already reserves for declarative rule tables.

### D-2. `SkillKind` and `TargetSpec` are forward-declared here, for change 8 to import.

Design doc §5.2 places `SkillDef.target_spec: TargetSpec` in this change's scope, but §6.2 describes
`TargetSpec` in the context of `ActionResolver`'s targeting validation — change 8's territory. This
change needs the enum *now*, as a field type on a dataclass it owns; change 8 needs the identical enum
later, to validate against. Rather than inventing two enums (or having change 8 block on this
change's exact timing), this change defines both enums as pure data with zero behavior:

```python
class SkillKind(StrEnum):
    ACTIVE = "active"
    PASSIVE = "passive"

class TargetSpec(StrEnum):
    NONE = "none"      # no target
    SELF = "self"       # self only
    SINGLE = "single"    # any present entity, including self
    AREA = "area"        # multi-select
```

This is the identical forward-declaration pattern change 2 → change 4 already used for `Subrace`
(flagged in change 2's design.md for change 4 to complete) and change 4 → this change already used for
`SKILL_REGISTRY` itself (flagged in change 4's design.md, D-5). `world/skills/registry.py`'s module
docstring states explicitly that change 8 (`action-resolver`) is expected to import these two enums
rather than redefine them, the same handoff discipline change 4's D-6 used for
`world/lore/sexual_vocab.py`.

**Alternative considered**: defining `TargetSpec` in a neutral, forward-owned location like
`world/rules/targeting.py` even though that module doesn't exist yet, and having this change import
a not-yet-created stub. Rejected — creating a stub file for a different change's not-yet-designed
module is worse than this change owning the two-enum forward declaration outright, since it would
put a placeholder file's shape on the record before change 8 has any say in it. `SkillKind` and
`TargetSpec` are small enough, and this change's need for them concrete enough, that authoring them
here (for change 8 to reuse) is no different from change 2 authoring `Subrace` for change 4 to
complete.

### D-3. `SkillDef` carries exactly design doc §5.2's seven fields — no more, no less.

```python
@dataclass(frozen=True)
class SkillDef:
    key: str
    kind: SkillKind
    target_spec: TargetSpec
    cost: dict[str, int]              # e.g. {"mp": 20, "sp": 5}; {} for most PASSIVE skills
    usable_out_of_combat: bool
    element: Element | None            # world.lore.elements.ELEMENT_REGISTRY entry, or None
    effects: list[str]                  # opaque effect IDs; see D-5 for the one convention this
                                          # change itself interprets
```

`element` references a real `Element` instance from change 2's `ELEMENT_REGISTRY` (not a bare string
key), matching design doc §5.2's literal type. `cost` and `effects` are transcribed verbatim from
§5.2's own comment (`{"mp": 20, "sp": 5}`, "effect IDs resolved against rulebook YAML"). No eighth
field (e.g. a `display_name_zh`, a `description`, or a `multiplier` field) is added, even though a
couple of this change's own seed skills (see D-5) would be marginally more self-documenting with one
— the task instruction is explicit that the field list is verbatim, and any felt need for an eighth
field is reported rather than silently added (see Risks).

### D-4. `SKILL_REGISTRY` is seeded with a representative set spanning every category the task
inventories, not an exhaustive transcription of the five sample cards.

Twenty-four entries, chosen to give each category from the task at least one concrete, inspectable
`SkillDef`:

| category | seed keys |
|---|---|
| stat multipliers | `body_enhancement` (×100), `body_enhancement_extreme` (×1000), `body_enhancement_basic` (judgment call, see below) |
| elemental mastery | `fire_mastery`, `dark_mastery`, `wind_mastery`, `light_mastery` (all `PASSIVE`, `element` set, `RankTitle` 主宰 referenced in `effects`) |
| direct spells | `fire_ball`, `wind_blade`, `flight` |
| weapon arts | `dual_wield_style`, `light_sword_style`, `shadow_slash`, `flash_step` |
| display-only | `status_disguise` |
| conferral | `dominion_art` (統御術) |
| passives | `defense_instinct`, `blade_art_mastery`, `extreme_endurance`, `magic_circle_comprehension`, `precise_mana_control`, `retainer_martial_training`, `guardian_instinct` |
| per-character unique passive | `reincarnation_boon_elosia`, `reincarnation_boon_yuka`, `reincarnation_boon_yuna` |

**Multiplier skills** (`body_enhancement*`) carry their multiplier inside `effects`, using the one
convention this change's own `SkillHandler` interprets directly (D-5): `effects=
["stat_multiply:atk_phys:100", "stat_multiply:agility:100", "stat_multiply:defense:100"]` for
`body_enhancement`; `...:1000` for `body_enhancement_extreme`. **Judgment call**: the source cards use
explicit `*100`/`*1000` notation for the two named tiers but show no notation at all for 基礎身體強化
(Lidzia's card lists it as a skill with no corresponding `*N` suffix on her stats) — this change
assigns it a modest `×1.2` (`stat_multiply:*:1.2`) as a placeholder "foundational, weaker than the
named tiers" value, documented here as invented rather than sourced, flagged for whoever eventually
needs a real balance number (change 9/16's territory, not this change's).

**Elemental mastery skills** are `PASSIVE`, `target_spec=NONE`, `cost={}` — representing "has reached
主宰 rank in this element" (change 2's `RANK_TITLE_REGISTRY["主宰"]`) rather than a single cast. Their
`effects` reference the rank by convention (`"element_mastery_rank:主宰"`), left opaque for change 6's
rulebook to interpret (e.g., as bonus elemental damage or unlocked ultimate-tier spells).

**統御術** (`dominion_art`) is `ACTIVE`, `target_spec=SINGLE`, `usable_out_of_combat=True` (Violet's
card shows it granted outside any combat context), `effects=["confer_skill_partial"]` — see D-6 for
the data model this effect ID names.

**狀態偽裝** (`status_disguise`) is `ACTIVE`, `target_spec=SELF`, `usable_out_of_combat=True`,
`effects=["set_disguise"]` — see D-7 for why this cannot violate D2 structurally.

**轉生特典** is not one registry key — it is a *pattern*. The three sample cards show three different
effects under the same Chinese label (Elosia: magic-growth rate; Yuka: combat prediction / 武感; Yuna:
sex-magic dominion), and `SkillDef` is a flat dataclass with no per-instance customization slot. Each
character's version gets its own registry key (`reincarnation_boon_<character>`), each a `PASSIVE`
with its own `effects` entry. This is documented explicitly so a future card author doesn't expect a
single shared `轉生特典` key to work for a new character with yet another unique effect — the pattern
is "one key per unique passive," not "one key reused across characters."

**What this does not do**: transcribe all ~35 distinct skill mentions across the five cards
verbatim. The task explicitly does not require that ("Cataloguing every individual skill is NOT
required — the registry shape plus a representative seed set is enough"); this seed set exercises
every field combination (`ACTIVE`/`PASSIVE`, all four `TargetSpec` values, `element` set and unset,
non-empty and empty `cost`) at least once.

### D-5. `SkillHandler.effective_value()` is the one and only resolution-time multiplier
application point; it never writes to `entity.traits`.

```python
# world/skills/handler.py
def _parse_stat_multiply(effect_id: str) -> tuple[str, float] | None:
    """Parses this change's own 'stat_multiply:<trait_key>:<multiplier>'
    convention. Every other effect ID is opaque and returned as None --
    change 6's rulebook engine owns interpreting the rest."""
    parts = effect_id.split(":")
    if len(parts) == 3 and parts[0] == "stat_multiply":
        return parts[1], float(parts[2])
    return None

class SkillHandler:
    def __init__(self, entity):
        self.entity = entity

    @property
    def _raw(self) -> dict:
        # entity.skills is change 3's seam attribute; change 4's loader already
        # writes {"active": [...], "passive": [...]} into it. Default to the
        # same shape for an entity never populated by the import loader.
        return self.entity.skills or {"active": [], "passive": []}

    def owned_keys(self) -> list[str]:
        return [*self._raw.get("active", []), *self._raw.get("passive", [])]

    def effective_value(self, trait_key: str) -> int:
        """THE resolution-time-only multiplier boundary. Reads
        entity.traits.<trait_key>.value (change 3's base value, per D-7) and
        returns a DERIVED number -- this function never assigns to
        entity.traits.<anything>.base or .mod. Combines every owned skill's
        matching stat_multiply effect (multiplicative) and every conferred
        grant at its own scale (see D-6)."""
        base = getattr(self.entity.traits, trait_key).value
        multiplier = 1.0
        for key in self._raw.get("active", []):
            skill = SKILL_REGISTRY.get(key)
            if skill is None:
                continue
            for effect_id in skill.effects:
                parsed = _parse_stat_multiply(effect_id)
                if parsed and parsed[0] == trait_key:
                    multiplier *= parsed[1]
        for grant in self.conferred_grants():
            if trait_key in grant.trait_keys:
                multiplier *= grant.scale
        return round(base * multiplier)
```

This function is deliberately a pure query — called by whatever needs an effective number, called
*by* nothing else in this change. It performs no resource check, no targeting, no side effect. A
regression test (mirroring change 3's D-9 source-scan tripwire) asserts `world/skills/handler.py`
contains no assignment to `entity.traits`, `.base`, or `.mod` anywhere, and a second test constructs
an entity with a known base value and a known active multiplier skill, asserting
`effective_value()`'s *return* value reflects the multiplier while `entity.traits.<key>.value` is
unchanged afterward — the same "derived, not written back" property change 3's D-7 tests for
construction-time values, now tested for resolution-time computation too.

**Why multiplicative combination across multiple owned multiplier skills, even though no sample card
shows a character stacking two multiplier tiers at once**: an entity could, in principle, register
both `body_enhancement` and `body_enhancement_extreme` as active simultaneously (nothing in this
change's registry shape prevents it), and this function must produce *some* well-defined answer
rather than picking one arbitrarily or raising. Multiplicative combination is the same rule already
used for combining a skill's multiplier with a conferred grant's `scale` — one uniform rule, not two.
Whether stacking should be *allowed* at the character-authoring or import-validation level is a
different, later question (change 8/9's territory), not this function's job to police.

### D-6. 統御術's partial-conferral: a `ConferredSkillGrant` data model plus a read-side fold-in,
cast-time creation deferred to change 8.

Violet's card shows the concrete shape this task calls "the most structurally awkward skill in the
set": she has no 身體強化 skill of her own, yet her `atk_phys`/`agility`/`defense` show a `×10`
suffix, and her status effects narrate this explicitly as "獲得「身體強化：...提升x100」的部份效果" —
a **partial** effect of Elosia's skill, scaled down from the source's ×100 to Violet's ×10.

```python
@dataclass(frozen=True)
class ConferredSkillGrant:
    source_key: str              # the granting entity's identifying key (not a SkillDef key)
    skill_key: str                # which of the source's skills is being partially granted
    trait_keys: tuple[str, ...]    # which traits this grant's multiplier applies to
    scale: float                   # the fraction of the source's own multiplier the recipient gets
                                     # (e.g. 0.1 -- Violet gets the source's x100 skill at x10, a
                                     # 1/10 scale-down, not a flat x10 constant)
```

Stored in a new, additive attribute, `entity.db.skill_grants: list[ConferredSkillGrant]`, requiring
**no edit to change 3's typeclass** — this is the identical pattern change 4's D-13 already used for
`entity.db.inventory` (a raw Evennia attribute-store attribute, not a declared seam). `SkillHandler`
gains:

```python
    def conferred_grants(self) -> list[ConferredSkillGrant]:
        return self.entity.db.skill_grants or []

    def grant_conferred(self, source_key: str, skill_key: str, trait_keys: tuple[str, ...], scale: float) -> None:
        """Records a grant. This is a plain data write -- it does not check
        that source_key currently owns skill_key, does not check resources,
        and is not itself the 'casting' of 統御術. Change 8's ActionResolver
        effect-resolution step is expected to call this after its own
        ownership/resource/target validation succeeds."""
        self.entity.db.skill_grants = [*(self.entity.db.skill_grants or []), ConferredSkillGrant(source_key, skill_key, trait_keys, scale)]
```

`effective_value()` (D-5) folds every matching grant's `scale` into its multiplier product. This
**is** built by this change — the data shape and the read-side computation are concrete and tested
(construct an entity with a `ConferredSkillGrant(scale=0.1, trait_keys=("atk_phys","agility",
"defense"))`, assert `effective_value("atk_phys")` reflects the ×10, not the source's ×100).

**What is deliberately deferred**: the actual *casting* of 統御術 during play — entity A selects
entity B as a target, `ActionResolver` validates the interaction, and only then is
`grant_conferred()` called with the right arguments — is change 8's job per this change's Non-Goals.
`grant_conferred()` exists now as the seam change 8 will call into, not as something this change's own
code path invokes autonomously.

**What is out of scope entirely, not merely deferred**: Violet's card also narrates a partial
*magic-growth-rate* effect from Elosia's 轉生特典 ("魔法成長百倍增幅" → Violet's unspecified partial
acceleration). This is not a combat-stat multiplier at all — it is a learning-rate/progression
concept with no obvious owning change in design doc §11 yet (progression/leveling is not explicitly
named against any roadmap item). Building a second, structurally different conferral mechanism for a
concept no later change has claimed would both blow this change's one-day budget and risk guessing
wrong about a system nobody has designed. **Decision**: this is named here as an explicitly unresolved
seam (see Open Questions), not implemented, and not silently folded into `ConferredSkillGrant` (which
is typed specifically around `trait_keys`/multiplicative `scale`, a shape that does not fit a
learning-rate concept without distortion).

**Alternative considered**: modeling 統御術 as a `BuffHandler` effect (change 6) instead of a
dedicated data model here, since a "temporary grant from another entity" sounds buff-shaped. Rejected
for this change's scope — change 6 does not exist yet, buffs are explicitly change 6's job (Non-
Goals), and design doc §5.1 already states skill multipliers are "a third, independent layer" distinct
from buffs; giving 統御術 its own small, additive data model keeps this change self-contained and
gives change 6 a clean later option to reimplement conferral as a buff if that turns out to be the
better long-term home — nothing here forecloses that.

### D-7. 狀態偽裝's effect resolution touches `entity.db.disguised_stats` and nothing else —
structurally, not just by convention.

```python
def apply_disguise_effect(entity, overrides: dict[str, int]) -> None:
    """The ENTIRE effect-resolution body for the status_disguise SkillDef.
    Sets change 3's D-8 storage convention directly. Contains no reference to
    entity.traits anywhere in this function -- there is no code path by which
    activating this skill could write a true trait value, satisfying D2
    (disguise is a pure display layer) by construction, not by discipline."""
    entity.db.disguised_stats = overrides
```

This is the entire function. A test asserts (a) calling it changes `entity.db.disguised_stats` and
leaves every `entity.traits.<key>.value` unchanged, and (b) — mirroring change 3's D-9 source-scanning
tripwire exactly — that `world/skills/handler.py` contains no reference to `entity.traits` inside or
near this function's definition. Because change 3 already built `get_display_value()` and the
`disguised_stats` storage, this change adds no new storage mechanism; it only registers 狀態偽裝 as a
`SkillDef` and supplies the one-line effect function that uses change 3's existing accessor
correctly. **Verification against D2**: the effect function has no parameter and no code path that
could reach `entity.traits`; the only way this skill could ever violate D2 is if a future edit adds
such a code path, which the regression test above catches the same way change 3's own tripwire test
catches a `combat.py` violation.

### D-8. Equipment slots borrow evadventure's wield-location structure, sized to what the sample
cards actually show, not evadventure's own slot count.

```python
class EquipmentSlot(StrEnum):
    WEAPON_MAIN = "weapon_main"
    WEAPON_OFF = "weapon_off"     # second weapon for dual-wielding (雙刀流) or a shield
    ARMOR = "armor"
    ACCESSORY = "accessory"        # multi-slot; see ACCESSORY_MAX_SLOTS below
```

The sample cards show exactly this shape: a single weapon or none (Lidzia's 輕劍, Violet's 無), a
dual-wielded pair occupying two hand slots at once (Yuka's 暗影鋼雙刀), one body-armor slot always
filled (every card's 防具), and a short list of accessories (Violet's one ring, Elosia's one earring,
others empty) — never more than a handful. **Flagged for implementer verification**, matching the
project's established discipline (changes 1–4) for any Evennia-contrib API assumption: this change
was designed without a locally installed Evennia package to confirm evadventure's actual
`WieldLocation` enum member names and `EquipmentHandler` method signatures against; the four-slot
shape above is this change's own design, *inspired by* the wield-location concept design doc §4 names
(one or two hands, body, a small accessory allowance), not a literal transcription of evadventure's
source. Whoever implements this change should confirm evadventure's real enum before wiring any
direct reuse, and adjust slot names only if doing so avoids gratuitous divergence — the four-slot
shape itself (not the exact member spelling) is this change's decision and does not depend on that
confirmation.

```python
class EquipmentHandler:
    ACCESSORY_MAX_SLOTS = 3   # judgment call -- no sample card or world_info.md source states a cap

    def __init__(self, entity):
        self.entity = entity

    @property
    def _raw(self) -> dict:
        # entity.equipment is change 3's seam attribute; change 4's loader already
        # writes the imported equipment dict into it verbatim. This change is the
        # first to define its canonical inner shape (change 4's schema only
        # required `type: object`, per its own Non-Goals deferring slot shape here).
        return self.entity.equipment or {
            "weapon_main": None, "weapon_off": None, "armor": None, "accessories": [],
        }

    def equip(self, slot: EquipmentSlot, item_key: str) -> None: ...
    def unequip(self, slot: EquipmentSlot) -> str | None: ...
    def slot_contents(self, slot: EquipmentSlot) -> str | list[str] | None: ...
```

**This change defines the canonical `entity.equipment` dict shape going forward** — change 4's
`CHARACTER_SCHEMA_V1.equipment` property only requires `{"type": "object"}` (its own Non-Goals defer
slot shape here explicitly: "equipment slot logic — change 5's job"). A card's raw `equipment: {}`
(the design doc §5.3 reference example) is a valid empty state under this shape (every slot `None`,
`accessories: []`); a populated one is expected to use these four keys. Whether `validate.py` should
eventually structurally check this shape is an open question this change does not resolve (change 4
is frozen and not edited by this change).

### D-9. Inventory stays a flat list of item-key strings — no capacity, weight, or stacking model.

```python
def add_item(entity, item_key: str) -> None:
    entity.db.inventory = [*(entity.db.inventory or []), item_key]

def remove_item(entity, item_key: str) -> None:
    items = entity.db.inventory or []
    if item_key in items:
        items = list(items)
        items.remove(item_key)
    entity.db.inventory = items

def list_items(entity) -> list[str]:
    return entity.db.inventory or []
```

`entity.db.inventory` is exactly the raw attribute change 4's D-13 already established (`entity.db
.inventory = record["inventory"]`, a raw list, "no seam attribute declaration required from any other
change"). These three functions are the entire inventory surface this change builds — no weight
limit, no stacking, no item-definition registry (an "item" is just a string key here; what that key
means — a weapon's stats, a potion's effect — belongs to whichever later change needs item
definitions, not named against any roadmap item yet). Sizing this any richer would not fit the
one-day budget and would guess at a system no roadmap item has claimed.

### D-10. `SkillHandler`/`EquipmentHandler` are facades constructed on demand, not descriptor-mounted
replacements of `entity.skills`/`entity.equipment` — because change 4's loader already writes plain
dicts to those exact attribute names.

Change 3's D-10 declared `skills`/`equipment` as `None`-defaulting `AttributeProperty` placeholders,
explicitly anticipating that this change would replace them "with a real handler mounted the same way
`traits` is mounted." But change 4's loader (already frozen, not edited by this change) writes
directly to those attribute names as plain data:

```python
entity.skills = {"active": record["skills"], "passive": record["passives"]}
entity.equipment = record["equipment"]
```

If `skills`/`equipment` became property-mounted handler objects with no setter (the way `entity.traits`
itself has no bare-assignment form — you call `.add()`, you don't do `entity.traits = {...}`), change
4's loader would break the moment it tried to assign a raw dict to a property with no setter. Since
change 4 cannot be edited (it is a separate, already-authored change), this change instead:

- **Leaves `entity.skills`/`entity.equipment` exactly as change 3/4 defined and populate them** — a
  plain, `None`-defaulting attribute holding a raw dict.
- **Adds two new properties to `typeclasses/entities.py`**, `skill_handler` and `equipment_handler`,
  each returning a freshly-constructed facade (`SkillHandler(self)` / `EquipmentHandler(self)`) that
  reads the raw dict as its data source. This is additive, not a replacement of the existing
  attribute's mounting — `entity.skills = {...}` (change 4's write) continues to work completely
  unmodified, and `entity.skill_handler.effective_value(...)` (this change's read API) is a new,
  parallel access path.

This satisfies change 3's D-10 anticipation ("replaced with a real handler") in spirit — there is now
a real handler object with real methods — without literally reusing `TraitHandler`'s exact mounting
mechanism, which assumes nobody ever bare-assigns to `entity.traits` (an assumption change 4 does not
share for `skills`/`equipment`). **Alternative considered**: asking change 4 to be edited to call
`entity.skill_handler.load(...)` instead of bare-assigning. Rejected outright — the task instructions
for this change are explicit that no other change's artifacts may be modified, and change 4 is
handed off/frozen per its own Milestones framing regardless.

### D-11. No combat-state branching anywhere in `world/skills/` — the `ActionResolver` seam is
declared, not built.

Design doc §5.2 states plainly: "A skill does not know whether it is in combat." Every function this
change adds (`effective_value()`, `grant_conferred()`, `apply_disguise_effect()`, `equip()`, the
inventory helpers) takes an entity (and, where relevant, a trait key or item key) and nothing that
resembles a combat-state flag, turn-order position, or `ActionResolver` context object. A regression
test inspects every public callable in `world/skills/handler.py` and `world/skills/equipment.py` via
`inspect.signature()` and asserts no parameter name matches `in_combat`/`combat_state`/`turn`/
`is_combat`, and a plain source-text check asserts the module bodies contain no conditional branching
on such a concept. This mirrors change 3's D-9 tripwire style (a deliberately simple, string/signature
-level check) rather than a heavier static-analysis tool, consistent with this change's one-day
budget.

## Risks / Trade-offs

- **[Risk] This change's own multiplier-resolution convention (`stat_multiply:<trait>:<multiplier>`
  encoded as a string inside `effects: list[str]`) is a string-parsing convention layered on top of
  a field design doc §5.2 describes as opaque "effect IDs resolved against rulebook YAML" — a future
  reader could mistake this for the real rulebook engine (change 6's job) rather than a narrow,
  self-contained parsing rule this change alone interprets.** → Mitigation: `_parse_stat_multiply()`'s
  docstring states explicitly that every other effect ID is left opaque for change 6, and this design
  doc's Non-Goals states the same boundary; the convention's prefix (`stat_multiply:`) is namespaced
  distinctly enough that change 6's eventual rulebook engine can either adopt it as one recognized
  effect kind among many, or leave it exactly as this change's own resolution-time shortcut.
- **[Risk] `SkillDef`'s frozen seven-field shape has no slot for a human-readable display name or a
  numeric multiplier field, which made two of this change's own seed skills (`body_enhancement*`)
  need to encode their multiplier as a string inside `effects` rather than a typed field.** →
  Reported per the task's explicit instruction ("if you need more, say so in your report") rather than
  silently added; the seven fields are transcribed verbatim from design doc §5.2 as instructed, and
  the `effects`-string convention (D-5) is this change's own accommodation, not a change to
  `SkillDef`'s shape.
- **[Risk] `body_enhancement_basic`'s ×1.2 multiplier is an invented placeholder number, not sourced
  from `world_info.md` or any card's explicit notation.** → Documented explicitly in D-4 as a judgment
  call, flagged for whoever eventually needs a real balance number (change 9's combat math or change
  16's progression tuning) — consistent with this project's established practice (change 1's D-4,
  change 2's D-1) of flagging invented numbers rather than presenting them as sourced.
- **[Risk] Multiple simultaneously-active multiplier skills combine multiplicatively with no upper
  bound or sanity check, which could in principle let a miscrafted character reach an absurd effective
  value.** → Accepted for this change's scope: `ActionResolver`/`dice-combat` (changes 8–9) are the
  natural place for any sanity clamp on effective combat power, since they are the actual consumers of
  `effective_value()`'s output; this change's job is the multiplication rule itself, not a balance
  ceiling on top of it.
- **[Risk] The 統御術 data model (`ConferredSkillGrant`) has no expiry, revocation, or duration —
  once granted, a grant persists in `entity.db.skill_grants` forever unless something explicitly
  removes it, which nothing in this change does.** → Accepted: duration/expiry is squarely
  buff-shaped machinery (change 6's `BuffHandler`), and this change's Non-Goals already exclude buffs;
  a grant here is a persistent fact ("this entity currently has a partial conferral from that entity"),
  and whether it should ever expire is a decision for whichever later change actually wires up the
  cast-time creation path (change 8) or reimplements conferral atop `BuffHandler` (change 6, if that
  turns out to be the better long-term home per D-6's alternative-considered note).
- **[Risk] `EquipmentHandler`'s four-slot shape (D-8) was designed without a locally installed
  Evennia package to verify evadventure's actual `WieldLocation` enum against, so it may diverge from
  evadventure's real member names or slot count in ways that make "borrowing its structure" a weaker
  claim than intended.** → Mitigation: flagged explicitly in D-8 for implementer verification,
  matching changes 1–4's identical discipline for unverified contrib-API assumptions; the four-slot
  shape itself is justified independently against the sample cards' own equipment data, not solely
  against evadventure, so it remains a reasonable design even if evadventure's exact enum differs.
- **[Risk] `typeclasses/entities.py` is a file change 3 authored; this change modifying it (D-10)
  could be read as overstepping change 3's boundary.** → Mitigation: change 3's own design.md D-10
  explicitly anticipates and names this exact replacement ("a plain placeholder attribute until its
  owning change replaces it with a real handler mounted the same way `traits` is mounted above"),
  and this change's edit is additive (two new properties) rather than a removal or behavioral change
  to anything change 3 built — `entity.skills`/`entity.equipment`'s existing mounting and change 4's
  write pattern are left completely intact.

## Migration Plan

Not applicable in the backward-compatibility sense — the project is unreleased with zero users, and
`world/skills/` currently contains no code at all. The only sequencing concern is operational: this
change must land after change 3 (needs `LivingEntity` and the `skills`/`equipment` seam attributes
importable) and should land in a way that change 4's already-written self-arming test
(`test_skill_registry_self_arming.py`) transitions from skipped to passing the moment
`world.skills.registry.SKILL_REGISTRY` is importable with genuine content — no code change to change 4
is required or made for that transition to happen.

## Open Questions

- **Who owns the partial magic-growth-rate conferral (Elosia → Violet's accelerated learning)?** No
  roadmap item in design doc §11 explicitly names progression/leveling mechanics. Left as an
  unresolved seam (D-6) rather than this change guessing at an owning change or a data shape for a
  concept nobody has designed yet.
- **Should `validate.py` (change 4, frozen) eventually structurally check `entity.equipment`'s inner
  shape against this change's four-slot convention (D-8)?** Change 4's schema currently only requires
  `{"type": "object"}`. This change does not, and cannot, edit change 4 to add that check; left open
  for whoever next touches the import contract.
- **Should a listed "active" vs. "passive" skill key (the two arrays change 4's loader already
  separates) be cross-checked against that key's own `SkillDef.kind`?** Not part of change 4's frozen
  reject/warn table, and not built here since it would require editing change 4's frozen validator.
  Left open for a future revision of the import contract, not this change's job.
- **Exact evadventure `WieldLocation` enum member names and `EquipmentHandler` method signatures**
  (D-8) are left to the implementer to confirm against the installed Evennia 6.1.0, the same
  verification discipline changes 1–4 already established for their own Evennia-API assumptions —
  this design doc could not verify them directly since Evennia is not installed in the environment
  this design was authored in.
