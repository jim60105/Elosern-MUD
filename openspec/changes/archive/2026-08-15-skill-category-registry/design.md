## Context

Full rationale lives in `docs/superpowers/specs/2026-08-15-skill-category-system-design.md`
(sections 1–4); this document covers only the implementation-level decisions needed to build this
specific change. That design document is the source of truth if anything here appears to conflict.

`SKILL_REGISTRY` is a module-level `dict[str, SkillDef]` built from a tuple literal of builder-
function calls (`_skill()`, `_spell()` via `_elemental_spells()`, `_body_multiplier()`). `SkillDef` is
a frozen dataclass whose `__post_init__` already validates presentation metadata, freezes its `cost`
and `effects` collections, parses `effects` into typed dataclasses, and validates heal-shape
consistency. `flee` is deliberately built outside `registry.py`, in `world/rules/disengage.py`,
because the `universal-action-ownership` spec requires `world/skills/` to have no dependency on
`world/rules/` — the innate-skill dependency runs the other way.

## Goals / Non-Goals

**Goals:**
- Every one of the 118 skills (117 in the registry + `flee`) declares exactly one `SkillCategory`.
- Classification is a presentation-only concern: no skill's `kind`, `cost`, `effects`, `element`,
  `target_spec`, or `faction_constraint` changes.
- An unclassified skill fails at import time, not silently at render time.
- The partition is provably exact and complete via structural tests, not by convention.

**Non-Goals:**
- No presentation changes. `combat_view.py`, `combat_panel.py`, `status_query.py`, and the telnet
  combat command are untouched here — they are `skill-category-combat-panel` and
  `skill-category-status-listing`.
- No derivation heuristic for `category` from any other field. See Decision D-1.
- No third classification level beyond `category`/`group`.

## Decisions

**D-1: `category` is a required dataclass field with no default; `group` is optional.**
Alternatives considered: (a) infer `category` from `element`/`kind`/`effects` — rejected, because it
demonstrably misclassifies real registry rows (`dual_blade_mastery`, `light_sword_style`, and
`shadow_slash` all carry an `element` but are `damage:<element>:physical` martial skills, not
elemental magic; `flight` carries `element="wind"` but is a movement passive); (b) a side-table
mapping key → category, mirroring how the sexual-act unlock metadata will live in a parallel
registry — rejected here because category is universal (every skill has exactly one), which is
precisely the test this project uses elsewhere to decide a field belongs on the dataclass itself
rather than in a side table.

**D-2: `SkillCategory` is a `StrEnum` with these eight members, in this declaration order:**
`ELEMENTAL_MAGIC`, `MARTIAL_ARTS`, `ENHANCEMENT`, `INNATE_GIFT`, `MOVEMENT`, `DIVINE_MYSTERY`,
`UTILITY`, `SEXUAL_ACT`. Declaration order is later consumed as display order by the presentation
changes, so it is fixed now even though nothing in this change renders it.

**D-3: `group: str | None`, validated non-empty when present, never derived from `element`.**
`_elemental_spells()` already receives one element for its whole spell set and can set `group` to
that element's key for free. The forthcoming sexual-act catalog will set `group` to its line name
the same way. Both are plain strings from the caller; there is no cross-category derivation logic.

**D-4: The exact classification table** (verified against a live registry dump during design; see
Testing Strategy below for how this is re-verified structurally rather than trusted as a static
table):

| Category | `group` | Members |
|---|---|---|
| `ELEMENTAL_MAGIC` | element key | 8 element-mastery passives + 79 elemental spells, of which **75** are built through `_elemental_spells()` (one edit; fire 10, water 10, earth 9, wind 8, lightning 8, ice 10, light 10, dark 10 — verified by AST-parsing the actual call sites, not assumed) and **4** are individually built `_skill()` calls requiring their own explicit classification: `hardened_skin` (earth), `gale_step` (wind), `static_ward` (lightning), `thunder_gods_haste` (lightning). All four are ACTIVE, SELF-target, `self_buff_apply:*`-effect skills — the same shape as already-bulk-classified entries like `water_shield`/`earthen_ward`/`ice_wall` — and are classified `ELEMENTAL_MAGIC` for that reason, not because of their `element` field alone (D-2's own caution about `element`-based derivation misclassifying `flight` applies equally here: the classification is a considered judgment about these skills' shape, not an automated rule). |
| `MARTIAL_ARTS` | `None` | `basic_attack`, `dual_blade_mastery`, `light_sword_style`, `shadow_slash`, `dual_wield_style` |
| `ENHANCEMENT` | `None` | `body_enhancement`, `body_enhancement_extreme`, `body_enhancement_basic` (all via `_body_multiplier()`, one edit), `defense_instinct`, `blade_art_mastery`, `extreme_endurance`, `retainer_martial_training`, `guardian_instinct`, `magic_circle_comprehension`, `precise_mana_control`, `concentration` |
| `INNATE_GIFT` | `None` | `reincarnation_boon_elosia`, `reincarnation_boon_yuka`, `elf_longevity` |
| `MOVEMENT` | `None` | `flight`, `flash_step`, `flee` (constructed in `disengage.py`) |
| `DIVINE_MYSTERY` | `None` | `divine_time_dilation`, `divine_space_distortion`, `divine_matter_transmutation`, `divine_life_extension` |
| `UTILITY` | `None` | `status_disguise`, `dominion_art` |
| `SEXUAL_ACT` | line name | `divine_sexual_arts` (`神之秘法`), `divine_sexual_mastery` (`精通`), `reincarnation_boon_yuna` (`精通`) |

**D-5: `flee`'s classification is declared at its construction site, not special-cased in the
registry.** Because `category` has no default, `world/rules/disengage.py`'s direct `SkillDef(...)`
construction fails to import until it supplies `category=SkillCategory.MOVEMENT`. This is the desired
fail-closed behavior and requires importing `SkillCategory` into `disengage.py` (a read of a plain
enum value, not a new dependency on `world/rules/` from `world/skills/`).

**D-6: The three sex-related skills move category.** `divine_sexual_arts`, `divine_sexual_mastery`,
and `reincarnation_boon_yuna` currently have no explicit category (this change is what introduces the
field), but their narrative home in the registry's construction order sits among the other divine
mysteries and innate-gift passives. They are classified `SEXUAL_ACT` here — a pure data change with
no effect on `requires_divine_arts`, cost, or any other mechanic — so a later sexual-act catalog
change can add ~69 more `SEXUAL_ACT` skills without a second move.

## Risks / Trade-offs

- **[Risk]** A future skill added to `_skill()`/`_spell()` without a `category` argument breaks the
  build immediately (missing required positional/keyword argument) rather than failing a lint or a
  test. → **Mitigation**: this is the intended behavior (see proposal's "Why"): fail at import time,
  not at render time. `SkillDef.__post_init__`'s existing validation style already does exactly this
  for effect strings and heal-shape consistency, so this is consistent with the module's established
  discipline, not a new failure mode to document separately.
- **[Risk]** Manually enumerating 118 classifications is error-prone (an off-by-one membership,
  a typo'd key). → **Mitigation**: the structural test in Testing Strategy computes
  `set(SKILL_REGISTRY.keys())` from the live registry (post-`disengage.py` import) and asserts it
  equals the union of the eight per-category sets with zero overlap — this fails loudly on any
  drift between this document's table and the actual code, and remains correct even as later changes
  add or remove skills, because it is not itself hardcoding a count. This exact risk materialized
  once already during this change's own design review: four individually-built elemental skills
  (`hardened_skin`, `gale_step`, `static_ward`, `thunder_gods_haste`) were initially omitted from the
  D-4 table and from tasks.md, which would have broken the registry's import entirely once `category`
  became a required field (§1's fail-closed behavior applying to the whole module, not just the four
  skills). Caught and corrected before implementation by cross-checking the table against an
  AST-level parse of every `_elemental_spells()` call site.
- **[Risk]** Thirteen test-only `SkillDef(...)` construction sites exist outside `registry.py` and
  `disengage.py`, across seven test files (`world/quests/tests/test_action_events.py`,
  `world/quests/tests/test_planner.py` ×2, `world/rules/tests/test_friendly_fire.py` ×2,
  `world/rules/tests/test_heal_effect_handler.py`, `world/rules/tests/test_effect_handlers.py`,
  `world/skills/tests/test_registry.py` ×6 of its 7 sites — one existing site,
  `test_constructing_without_metadata_fails_closed`, already expects `TypeError` for missing
  `label`/`description` and needs no change, since a missing `category` also raises `TypeError`).
  Several are module-level constants evaluated at import time, so once `category` has no default,
  those test *modules* fail to collect at all — breaking unrelated tests in the same files, not just
  the specific skill-construction assertions. Two of `test_registry.py`'s sites are inside
  `assertRaises(ValueError)` blocks testing an unrelated validation failure (empty label, oversized
  description); without an added `category` argument, construction would raise `TypeError` first,
  which `assertRaises(ValueError)` does not catch, turning an intended-failure test into a test
  error. → **Mitigation**: every site gets an explicit `category` argument added in the same commit
  (Testing Strategy's task group), verified by running the full non-browser Evennia suite and the
  `tests/` contract suite, not just the tests this change directly adds.

- **[Risk]** The `skill-registry` capability's existing "Skills declare only self-only or free target
  scope" requirement enumerates `SkillDef`'s field set as exactly ten fields and asserts every
  production entry supplies all ten directly; this change adds two more (`category`, `group`)
  without listing `skill-registry` as a Modified Capability or updating that count. →
  **Mitigation**: not a functional contradiction — the ten-field assertion remains literally true,
  since this change only adds fields, never removes or renames one the existing requirement counts.
  Left as a known, accepted staleness rather than opened as a delta here, to avoid touching a
  677-line spec file for a field-count comment; noted so a future reader of `skill-registry`'s spec
  is not surprised to find `SkillDef` has grown two fields it does not mention.

## Migration Plan

Not applicable — this project has no released users and no backward-compatibility obligation. The
change lands as a single atomic commit: `SkillCategory` added, both fields added to `SkillDef`, all
118 classifications supplied in the same commit (a partially classified registry cannot import, by
design), structural tests added and green.

## Open Questions

None. All classification decisions were made during the design-document phase
(`2026-08-15-skill-category-system-design.md` §3) and are treated as settled inputs to this change.
