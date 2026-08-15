# Skill Category System — Design

**Date:** 2026-08-15
**Status:** Approved (pending final user review)
**Scope:** `world/skills/registry.py`, `world/rules/disengage.py`, `world/rules/combat_view.py`,
`world/rules/status_query.py`, the `context_actions` presentation schema, `webclient-combat-menu`
spec deltas.

Part of the [Sexual Act System document set](2026-08-15-sexual-act-system-overview-design.md).
This is the **prerequisite** change: proposals `A1`, `A2`, `A3` in that document's §4.

This change stands on its own merits and is worth landing regardless of the sexual act system. It is
sequenced first because it makes 69 new acts cost **zero UI work** — they declare a category and
appear in the right place.

---

## 1. Problem Statement

`SKILL_REGISTRY` holds 117 skills defined in `world/skills/registry.py`, plus `flee`, which
`world/rules/disengage.py` injects at import time — **118 total**. They are presented as one flat,
unsorted array.

The composition is heavily skewed:

| Shape | Count |
|---|---|
| Elemental spells (8 elements × ~10) | 79 |
| Element mastery passives | 8 |
| Everything else | 31 |

The combat panel (`world/rules/combat_view.py`) renders every owned ACTIVE skill from
`SkillHandler.owned_keys()` in ownership order with no grouping. For a high-level caster this is
already a long undifferentiated list. Adding the sexual act catalog would push it past usable.

Two secondary defects surface from the same root cause:

- **The out-of-combat listing is wrong, not merely ungrouped.** `world/rules/status_query.py:357`
  reads the raw `entity.db.skills` attribute rather than `SkillHandler.owned_keys()`. Because
  `INNATE_SKILL_KEYS` are contributed by `owned_keys()` and never written to `entity.db.skills`,
  **`flee` and `basic_attack` are invisible in the out-of-combat listing today** while appearing
  correctly in combat. Any grouped listing must fix the source, not just the presentation.
- **There is no place to declare presentational intent**, so any grouping would have to be inferred
  from existing fields — which cannot work (see D-2).

---

## 2. Architectural Decisions

| # | Decision | Rationale |
|---|---|---|
| D-1 | **Two new fields on `SkillDef`: `category: SkillCategory` (required, no default) and `group: str \| None` (optional second level).** | Category is genuinely universal — every skill has exactly one — which is the test for belonging on the dataclass rather than in a side table. Contrast the sexual acts' unlock/participant metadata, which only 69 of an eventual 187 skills would ever set and therefore lives in a parallel registry (overview D-1). Making `category` required with no default means a new skill cannot silently land in a junk bucket; it fails at registry-load time, consistent with `parse_effect`'s existing "unrecognized prefix raises at import, not at use" discipline. |
| D-2 | **Category is explicitly declared, never derived from `element`, `kind`, `effects`, or `target_spec`.** | Derivation demonstrably misclassifies. `basic_attack`, `dual_blade_mastery`, `light_sword_style`, and `shadow_slash` all carry an `element` but declare `damage:<element>:physical` — they are 武技, not 元素魔法. `flight` carries `element="wind"` but is a movement passive. `dual_blade_mastery` even ends in `_mastery` without being an element mastery. Every candidate heuristic breaks on real registry rows. |
| D-3 | **`group` is a plain nullable string, filled by the builder functions, not derived from `element`.** | `_elemental_spells()` already receives the element once for a whole set and can set `group` for free; sexual acts will set the line name. Deriving `group` from `element` would work for one category and be meaningless for the other, requiring a per-category branch in the presenter. A stored string keeps the presenter uniform: read `category`, read `group`, render. |
| D-4 | **The taxonomy axis is "what the player does with it", not "what it looks like in data".** | This is why `light_sword_style` (a sword art that happens to deal light damage) is `martial_arts` while `light_arrow` is `elemental_magic`. A player looking for their sword techniques will not think to check the light-magic page. |
| D-5 | **The three existing sex-related skills move from `divine_mystery`/`innate_gift` into `sexual_act`.** Their acquisition paths (`requires_divine_arts`, race/reincarnation) are untouched; only the display location changes. | A player who owns 性魔法主宰 will look for it under 性愛行為. Category is a presentation concern by construction (D-1's field lives beside `label` and `description`, not beside `cost` or `faction_constraint`), so moving a skill between categories can never change a mechanic. |
| D-6 | **`flee`'s category is declared at its construction site in `world/rules/disengage.py`**, not special-cased in the registry. | `flee` is deliberately constructed outside `registry.py` (the `universal-action-ownership` spec requires `world/skills/` not to depend on `world/rules/`, so the dependency runs the other way). Because `category` is required, `disengage.py` fails to import until it declares one — the desired fail-closed behaviour, and the reason `A1` owns `disengage.py` as well as `registry.py`. |

---

## 3. The Taxonomy

Eight categories. Counts are the current registry; the sexual act system adds 69 to `sexual_act`
(62 counter-gated plus 7 神之秘法).

| Key | Label | Second level | Count | Members |
|---|---|---|---|---|
| `elemental_magic` | 元素魔法 | **element key** | 87 | 8 element masteries + 79 elemental spells |
| `martial_arts` | 武技 | — | 5 | `basic_attack`, `dual_blade_mastery`, `light_sword_style`, `shadow_slash`, `dual_wield_style` |
| `enhancement` | 強化 | — | 11 | `body_enhancement` ×3, `defense_instinct`, `blade_art_mastery`, `extreme_endurance`, `retainer_martial_training`, `guardian_instinct`, `magic_circle_comprehension`, `precise_mana_control`, `concentration` |
| `innate_gift` | 天賦 | — | 3 | `reincarnation_boon_elosia`, `reincarnation_boon_yuka`, `elf_longevity` |
| `movement` | 移動 | — | 3 | `flight`, `flash_step`, `flee` |
| `divine_mystery` | 神之秘法 | — | 4 | `divine_time_dilation`, `divine_space_distortion`, `divine_matter_transmutation`, `divine_life_extension` |
| `utility` | 特殊 | — | 2 | `status_disguise`, `dominion_art` |
| `sexual_act` | 性愛行為 | **line** | 3 (+69) | `divine_sexual_arts`, `divine_sexual_mastery`, `reincarnation_boon_yuna` |

**118 total.** Verified to partition the registry exactly: no skill unassigned, no assignment naming
an absent key.

### 3.1 `elemental_magic` second level

`group` is the `Element.key` (`fire`, `water`, `earth`, `wind`, `lightning`, `ice`, `light`,
`dark`). Each element's page therefore contains its mastery passive alongside its spells.

Per-element counts: seven elements hold 11 each (mastery + 10 spells); **wind holds 10** because
`flight` is categorised `movement` rather than `elemental_magic` despite carrying `element="wind"` —
a direct illustration of D-2.

### 3.2 `sexual_act` second level

`group` is the line name: `獨處`, `羞恥`, `關係`, `戰鬥`, `異種`, `神之秘法`, `精通`. The three
existing skills take `神之秘法` (`divine_sexual_arts`) and `精通` (`divine_sexual_mastery`,
`reincarnation_boon_yuna`). See the [Act Catalog](2026-08-15-sexual-act-catalog-design.md).

### 3.3 Categories with no second level

`group` is `None` for the other six categories. The presenter renders a single ungrouped list in
that case — one code path, no per-category branching.

---

## 4. Registry Changes

`SkillCategory` is a `StrEnum` in `world/skills/registry.py`, alongside the existing `SkillKind`,
`TargetSpec`, and `FactionConstraint`.

The 118 assignments are made almost entirely through the existing builder helpers, so the diff is
far smaller than the count suggests:

- `_elemental_spells()` sets `category=ELEMENTAL_MAGIC` and `group=<element>` for all 79 spells from
  the element it already receives. **One edit covers 79 rows.**
- `_body_multiplier()` sets `category=ENHANCEMENT` for its 3 rows. **One edit covers 3.**
- The 8 element masteries are built by individual `_skill()` calls and take an explicit argument.
- The remaining ~28 individual `_skill()` calls take an explicit argument each.
- `world/rules/disengage.py`'s direct `SkillDef(...)` for `flee` takes an explicit argument (D-6).

`_skill()` and `_spell()` gain a required `category` parameter and an optional `group`. Because
`SkillDef.category` has no default, every construction path is forced to supply one.

### 4.1 Validation

`SkillDef.__post_init__` — which already validates presentation metadata, freezes collections,
parses effects, and checks heal shape — gains one check: `group`, when present, must be a non-empty
string. Category validity is enforced by the enum type itself.

---

## 5. Presentation Contract

### 5.1 Combat panel: `context_actions` v2 → v3

The `webclient-combat-menu` spec currently requires the available payload to contain *exactly*
`schema_version`, `available`, `kind`, `session`, `participants`, `root_actions`,
`secondary_actions`, and `skills`, and requires `skills` to list each owned active `SkillDef` in
`owned_keys()` order.

Version 3 changes `skills` from a flat array of skill descriptors into an ordered array of
**category groups**:

```
skills: [
  {
    category: "elemental_magic",      # stable key, 1..32 ASCII
    label: "元素魔法",                 # bounded display label
    groups: [                          # ordered; a single null-key group when the
      {                                # category has no second level
        group: "fire" | null,
        label: "火" | null,
        skills: [ <unchanged v2 skill descriptor>, ... ]
      }, ...
    ]
  }, ...
]
```

Three properties are preserved deliberately:

- **The individual skill descriptor is byte-identical to v2.** Its key, label, description, cost,
  target spec, element, enabled state, disabled reason, valid participant IDs, and AREA shorthands
  are unchanged. Only the nesting changes, which keeps the browser-side action dispatch untouched.
- **Ordering within a group remains `owned_keys()` order**, with no alphabetical reordering — the
  existing requirement is inherited verbatim, one level deeper.
- **Category ordering is the `SkillCategory` enum's declaration order**, and group ordering within
  `elemental_magic` is `ELEMENT_REGISTRY` order. Both are fixed, deterministic, and independent of
  what the entity happens to own.

**Empty categories and empty groups are omitted**, not emitted with an empty array. A player who
owns no sexual acts sees no 性愛行為 category at all — which is exactly the "hide, do not disable"
requirement, satisfied one level up from where the overview document's D-2 satisfies it for
individual acts.

### 5.2 Telnet parity

The combat menu spec requires full Telnet parity. The text rendering gains a category heading and,
where a second level exists, a sub-heading, using the same ordering rules.

### 5.3 Out-of-combat listing

`world/rules/status_query.py` switches from raw `entity.db.skills` to `SkillHandler.owned_keys()`
and applies the identical grouping. This is a **behaviour fix**, not just a presentation change:
innate skills become visible out of combat for the first time (§1).

---

## 6. Error Handling & Validation

| Condition | Behaviour |
|---|---|
| A skill constructed without `category` | `TypeError` at registry-load time (missing required argument). Import fails; the server does not start with an unclassified skill. |
| `group` present but empty or non-string | `ValueError` from `__post_init__`, naming the skill key. |
| A category with no members | Omitted from the payload. Not an error — a player owning nothing in a category is the normal case. |
| A presenter failure | Unchanged from today: `context_actions` becomes correlated-unavailable in isolation while status and narrative stay healthy, per the existing spec requirement. |

---

## 7. Testing Strategy

**Structural tests** (following the `sexual.yaml` precedent of enforcing coverage structurally
rather than by convention):

- Every key in `SKILL_REGISTRY` has a `category` that is a valid `SkillCategory` member — asserted
  after importing `world.rules.disengage`, so `flee` is in scope.
- The union of the per-category member sets equals `SKILL_REGISTRY.keys()` exactly: no skill
  unassigned, no assignment naming an absent key. This is the check that caught `flee` living
  outside `registry.py` during design.
- Every `elemental_magic` member has a non-null `group` that is a key of `ELEMENT_REGISTRY`.
- Every `sexual_act` member has a non-null `group`.
- Every member of the other six categories has `group is None`.

**Presentation tests:**

- Node tests for the v3 payload shape, including the omitted-empty-category case.
- Browser acceptance for the grouped combat menu. **This is the runtime-expensive part of the
  change**: combat browser tests boot one Evennia server per test (~35–70 s each), which is why the
  overview document schedules `A2` as a full day with no parallel track for the same implementer.
- Telnet parity assertions on heading order and membership.
- An out-of-combat listing test asserting `flee` and `basic_attack` are now present — the §1 defect,
  pinned so it cannot regress.

---

## 8. Explicitly Out of Scope

- **Player-configurable category ordering or favourites.** Ordering is enum-declaration order.
- **Filtering or search within the panel.** Grouping is sufficient for the observed sizes.
- **Sub-categories deeper than two levels.** `group` is a single nullable string; if a third level
  is ever needed it is a separate proposal.
- **Re-costing or rebalancing any skill.** This change moves nothing but presentation metadata.
