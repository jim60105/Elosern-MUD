## Why

`SexualState.arousal` is a five-level `OrderedLevelTrait` (`平靜/微興奮/中等/高度/極限`), and the only
production rule that raises it (`arousal_up_on_stimulus`) applies `+1..+2` per stimulus — three
stimuli reach the maximum. This resolution cannot express the forthcoming sexual act catalog's 69
acts of differing magnitude, cannot carry a sensitivity multiplier that rewards repeated stimulation
of one body part, and cannot support a meaningful "keep pushing to extend a climax" threshold. Every
downstream mechanic in the [sexual act system](../../../docs/superpowers/specs/2026-08-15-sexual-act-system-overview-design.md)
needs a finer-grained, formula-friendly arousal quantity before any act can be built on top of it.

This is proposal `B1` in that document set's [Sexual Pleasure Model](../../../docs/superpowers/specs/2026-08-15-sexual-pleasure-model-design.md)
§1, scheduled in the set's first parallel batch with no dependency on any other proposal.

## What Changes

- Add `pleasure`, a new `0..100` bounded counter field on `SexualState`, as the **authoritative**
  arousal quantity.
- **BREAKING** (pre-release, no migration needed per `AGENTS.md`): `arousal` becomes a **derived,
  read-only** view computed from `pleasure` via a five-band lookup table. It keeps its
  `OrderedLevelTrait`-shaped comparison surface (`.value`, `.level`, `.levels`, `==`, `>=`, `>`, `<=`,
  `<`) so every existing *reader* (`combat_modifiers.yaml`'s `high_arousal_agility_accuracy_penalty`,
  `overwhelm.py`, `status_display.yaml`) continues to work with **no edit to any of those three
  files**. Direct assignment (`entity.sexual.arousal.value = ...`) is no longer supported; the
  twenty existing test call sites that do this are migrated to set `pleasure` instead (see tasks.md).
- Add `world/rules/rulebook/sexual_pleasure.yaml`: the five-band `pleasure → arousal` lookup table,
  plus the sensitivity and shame gain-multiplier tables the forthcoming act-effects proposal (`B5`)
  will consume. Loaded and validated by a small dedicated Python loader (following the
  `world/rules/rulebook/affinity.yaml` / `affinity_config.py` precedent — a plain, hand-validated
  configuration table, not `world.rules.rulebook.schema.load_rules()`'s `id`/`when`/`then` rule
  shape, which does not fit a range-lookup table).
- Rewrite the four `sexual.yaml` rules that currently target `arousal` (`arousal_up_on_stimulus`,
  `arousal_up_on_sustained_stimulus`, `arousal_extreme_stimulus_to_max`,
  `arousal_reset_after_climax`) to target `pleasure` instead, each keeping its `id`. `FIELD_KINDS` in
  `sexual_transitions.py` gains a `pleasure` entry and loses its `arousal` entry.
- Redesign `decay_tick`'s arousal handling to decay the numeric `pleasure` value down to exactly one
  band below its current one per elapsed interval, preserving the "at most one level of decay"
  behaviour observably even though the underlying field is now numeric.
- Migrate the twenty existing `entity.sexual.arousal.value = ...` test call sites (nine test files)
  to set `entity.sexual.pleasure.base` at the target band's floor instead.
- Teach the two existing **no-create** raw-storage readers —
  `world/rules/combat_modifiers.py::_stored_sexual_level()` (feeding skill-cast preview/preflight) and
  `world/rules/status_query.py::_sexual_level()` (feeding the player-facing status panel) — to resolve
  the derived arousal level from the newly-stored `pleasure` counter instead of a now-absent raw
  `"arousal"` key, so neither silently freezes at a character's import-time baseline once `pleasure`
  starts changing at runtime. **Found during review, not in the original scope of this proposal —
  see design.md D-7.**

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `sexual-state-handler`: adds requirements for `pleasure`'s construction (from an imported
  baseline's `arousal` level string, and for entities with none) and its decay behaviour. No
  existing requirement's text changes — every observable scenario in this capability remains true
  after this change (see design.md D-2 and D-5 for the point-by-point check) — these are `ADDED
  Requirements`.
- `sexual-transition-rulebook`: `MODIFIED` — "Ordered-level field rules write through the field's own
  live trait object, never through a second write path" no longer covers `arousal` (no rule targets
  it via `then.field` anymore); its two `arousal`-example scenarios are replaced with equivalent
  `wetness`-example scenarios that still exercise the same `OrderedLevelTrait`-mutation mechanism the
  requirement is actually about.
- `combat-modifier-table`: `ADDED` — one new requirement pinning that the no-create preview/preflight
  path (`build_no_create_condition_context()`) resolves `pleasure`'s stored value to the correct
  derived arousal level, matching what the live, handler-based `evaluate_combat_modifiers()` path
  already reports for the same entity.
- `webclient-status-presentation`: `ADDED` — one new requirement pinning the same resolution for the
  status panel's no-create read model, preserving the existing "Sexual threshold appears only while
  matched" and "Unmaterialized sexual baseline remains unmaterialized" requirements' observable
  behaviour under the new `pleasure`-backed representation (no existing requirement text in this
  capability changes).

## Impact

- `world/rules/sexual_state.py` — `pleasure` field, derived `arousal` view, band-lookup helper,
  redesigned decay branch for `pleasure`.
- `world/rules/rulebook/sexual.yaml` — four rules retargeted, ids unchanged.
- `world/rules/rulebook/sexual_pleasure.yaml` — new file.
- `world/rules/sexual_transitions.py` — `FIELD_KINDS` entry swap, one new `_apply_then()` branch, one
  new context/change-reporting rule (see design.md D-4).
- `world/rules/combat_modifiers.py` and `world/rules/status_query.py` — one new branch each in their
  respective raw-storage sexual-level readers (design.md D-7). Neither file's `evaluate_condition()`
  usage, merge logic, or any other behaviour changes; only the `field == "arousal"` raw-lookup path.
- Nine test files (twenty call sites) migrated: `test_combat_modifiers.py`,
  `test_combat_modifiers_self_arming.py`, `test_combat_modifiers_matched.py`,
  `test_sexual_transitions.py`, `test_sexual_state.py`, `test_sexual_decay_and_reset.py`,
  `test_monster_sexual_baseline.py`, `test_status_query.py`, `test_status_boundary.py`.
- No change to `world/rules/rulebook/combat_modifiers.yaml`, `world/rules/overwhelm.py`, or
  `world/rules/rulebook/status_display.yaml` — the entire point of keeping `arousal` comparable.
  (`world/rules/combat_modifiers.py` and `world/rules/status_query.py` — the *Python modules*, not
  these YAML/overwhelm files — do change, per D-7 above; this bullet is specifically about the
  condition-evaluation and display-metadata surfaces staying untouched.)
- Independent of `exposure-combat-modifier` (already proposed, reads `exposure` only) and of every
  other proposal in the sexual act system set; `sexual-counters` (`B2`) depends on this proposal
  landing first.
