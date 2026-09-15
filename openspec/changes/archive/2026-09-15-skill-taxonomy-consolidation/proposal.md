# Phase B — SkillCategory taxonomy consolidation

## Batch:

depends-on: light-spell-catalog
depends-on: light-cleric-feedback
depends-on: light-climax-empowerment
depends-on: light-sacrament-casting
depends-on: light-penance-events
depends-on: light-sustained-recovery
depends-on: light-judgment-traits
code-conflict: world/skills/registry.py — light-spell-catalog (wave order 10) rewrites the light rows of this same registry file and owns the post-archive skill-registry main-spec sync; light-sacrament-casting's surfaces also name this file. This change edits the category enum and the MOVEMENT/INNATE_GIFT construction sites in the same file. Zero delta-spec requirement overlap, but same-file + same-capability ownership → apply strictly after the seven active light changes are implemented, archived, and their deltas synced (light-effect-potency / light-divinity-tier / light-effect-routing are already archived+synced).
code-conflict: world/skills/tests/test_skill_registry.py — light-spell-catalog removes the light echo tests from this file; this change rewrites `_CATEGORY_ORDER`, `_UNGROUPED_CATEGORIES`, and the D4 classification-table test in the same file. Serialize behind change 10.

## Why

The eight-member `SkillCategory` enum conflates three genuinely different mechanic families with two display-only branches. `MOVEMENT` and `INNATE_GIFT` are not mechanic families at all: `flight`/`flash_step` are acquisition-granted PASSIVE waivers (D8 of the 2026-08-12 redesign), `elf_longevity`/`reincarnation_boon_*` are acquisition-granted PASSIVE traits — the same skill shape as the `ENHANCEMENT` passives that `docs/lore/skill-trees/enhancement.md` already documents as one acquisition-condition-keyed table. Keeping them as top-level branches forces every presentation surface (combat panel, character panel, protocol validator mirror, lineage labels) to carry two extra buckets whose only distinction is narrative provenance, and it forces lore docs to describe a taxonomy (`magic-system.md` §2's eight-branch table) that the mechanics do not support. This is Phase B of the post-Phase-A taxonomy cleanup; the seven non-light element trees' re-authoring is Phase C and is not touched here.

## What Changes

- **BREAKING** (presentation data contract, pre-release, zero users): `SkillCategory.MOVEMENT` and `SkillCategory.INNATE_GIFT` are retired as enum branches. The enum drops to six members. The eight-branch taxonomy in `docs/lore/magic-system.md` §2 collapses to the three ratified mechanic families:
  1. **Prerequisite-DAG skill 譜** — `ELEMENTAL_MAGIC`, `UTILITY`, `MARTIAL_ARTS`, `DIVINE_MYSTERY`: one mechanism, three parameters (resource axis MP / SP / zero-cost, learning cadence use-count vs research-digest, divine gate). Unchanged mechanically.
  2. **Acquired-passives bucket** — `ENHANCEMENT` absorbs the former `MOVEMENT` passives (`flight`, `flash_step`) and the former `INNATE_GIFT` traits (`elf_longevity`, `reincarnation_boon_elosia`, `reincarnation_boon_yuka`), keyed by acquisition condition exactly as `docs/lore/skill-trees/enhancement.md` already formats. `MOVEMENT`/`INNATE_GIFT` survive only as display-level groups inside the bucket: the two movement passives declare `group="身法"`, the three trait rows declare `group="天賦"`, every other enhancement member keeps `group=None`. Both presenters already render a non-elemental `group` verbatim as its label, so no new label plumbing is needed.
  3. **`SEXUAL_ACT` catalog** — deliberately independent, untouched.
- `flee` (currently `MOVEMENT`, registered by `world/rules/disengage.py` at its own construction site per the universal-action-ownership requirement) moves to `MARTIAL_ARTS`, pairing it with its `INNATE_SKILL_KEYS` sibling `basic_attack`. Its waiver/disengage mechanics are untouched.
- **Preserved verbatim, categorization-only change**: the typed-effects engine (`movement:flight`/`movement:flash_step` parse and `MovementEffect`), the D8 wilderness-cost waiver in `world/rules/movement.py`, `stat_multiply` handling of the body-enhancement family, the `skill_owned` rule rows in `world/rules/rulebook/combat_modifiers.yaml`, and every `requires_divine_arts` cast gate. No effect string, kind, cost, element, or target field of any re-homed skill changes.
- Presentation-metadata re-homing: `CATEGORY_LABELS` in `world/rules/combat_view.py`/`status_query.py` lose two entries and gain the acquisition-group label; `web/static/webclient/js/elosern/protocol.js`'s `SKILL_CATEGORY_KEYS` mirror drops to six keys; the client validator's category-count bound (tied to `SKILL_CATEGORY_KEYS.length`) follows automatically.
- Delta specs modify presentation/categorization requirements only (details in design.md). Investigation locates the categorization/presentation requirements in `skill-category-registry`, `universal-action-ownership`, and the two webclient menu capabilities — those are the delta targets. `skill-registry`'s own main-spec requirements are untouched by this delta (its `category`-field contract and per-element spell-set requirements don't pin the two retired enum members); no light behavioral requirement is touched, and the re-homing assumes the post-`light-spell-catalog` synced snapshot.
- No migrations or compatibility layers: the seven non-light element catalogs are dev-era data that a later skill-trees-driven change will wholesale replace; this change does not touch any spell row.

## Out of scope (explicit non-goals)

- The light tree itself: all 16 light nodes stay `ELEMENTAL_MAGIC` group `light`, untouched (they don't exist yet — `light-spell-catalog` registers them).
- The `SEXUAL_ACT` category and the `SEXUAL_ACT_REGISTRY` counter mechanism — deliberately independent by design, stays.
- All light-wave typed-effect machinery (changes 1–9 of the 2026-08-12 §11 roadmap).
- Player command surface: no `docs/game/commands.md` impact expected — verified (investigation: that file's movement section lists 進入/前往/地圖/看/回家/離開-style commands; flight/flash_step are passive ownership waivers with no command, and no command doc names the categories).
- Re-authoring the seven non-light element trees (Phase C), any spell-row data edits, and any migration of dev-era registry rows.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `skill-category-registry`: six-member enum in fixed order; group rule extended so `enhancement` members may declare the closed acquisition-tag vocabulary (`None` | `"acquisition:innate"`); partition requirements re-pinned to the re-homing table.
- `universal-action-ownership`: `flee declares its skill category at its own construction site` re-pinned from `MOVEMENT` to `MARTIAL_ARTS` (still declared at the construction site, still explicit).
- `webclient-combat-menu` / `webclient-exploration-menu`: the shared grouping rule's category set drops two members; the `movement`-before/after-ordering and innate-`flee`-under-`movement` scenarios re-pin to `enhancement`/`martial_arts` presentation; group semantics for `enhancement` follow the acquisition tag.

## Impact

`world/skills/registry.py` (enum + 5 construction sites), `world/rules/disengage.py` (1 kwarg), `world/rules/combat_view.py` + `world/rules/status_query.py` (label maps + enhancement group branch), `web/static/webclient/js/elosern/protocol.js` (mirror + bound; `CHARACTER_MAX_CATEGORY_GROUPS = 9` comment/bound shrinks to 7 to mirror Python's dynamic `len(SkillCategory)+1`). Test/helper consumers that import the retired members and must be re-kwarged or re-pinned: `world/skills/tests/test_skill_registry.py` (contracts + `FleeCategoryDeclarationTests`), `world/rules/tests/test_movement.py` (module-level `_DART_STEP` synth skill), `world/rules/tests/_combat_session_helpers.py` (`synth_innate_overlay()`'s flee row — shared by 15+ test modules), `world/rules/tests/test_status_query.py` (module-level `_ROW_REST` category tuple), `web/browser_support/browser_fixtures_data.py` (synth flee row grafted into browser-seed catalogs), `webclient/presentation/tests/test_combat_panel.py` + `test_character_panel.py`, `web/tests/browser/test_browser_combat.py` (`_open_category(page, "movement")` navigation + the enum-order panel assertion), JS: `protocol.test.js`, `combat_menu.test.js`, `character_menu.test.js`, `web/webclient-app/tests/preserved_contract.test.js` (`innate_gift` fixture payload) and the `web/webclient-app` story/store fixtures where the eight-key list appears. Lore docs: `docs/lore/magic-system.md` §2/§5/§7/§8, `docs/lore/skill-trees/index.md` §7, `docs/lore/skill-trees/enhancement.md`/`innate-gift.md`/`movement.md`. Shard/traceability impact: none expected — the change edits existing test modules (each keeps its existing shard owner) and adds no new test modules to `tools/test_data_freeze.json`. Apply-phase serialization behind the archived light wave is mandatory; see design.md.
