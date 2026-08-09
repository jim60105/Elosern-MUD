## Why

`disguised_stats`'s third consumer (master design D2) is a forward-declared seam: the docstring
and boundary test name "appraisal items", but no appraisal mechanic exists and no player surface
reads a target's displayed values. The owner decided displayed stats are a first-class system
mechanic — the player reads any present target's displayed combat values directly from
`look <target>`, with no item and no service.

## What Changes

- New shared renderer `display_stat_block(entity)` in `world/rules/displayed_stats.py` producing
  the displayed combat five (`atk_phys`, `agility`, `defense`, `magic_level`, `hp`) through
  `get_display_value()`, in fixed order with the canonical character-panel labels, returning
  `None` for non-living targets.
- `look <target>` (text 「看」) appends the block after the target's description; bare `look`
  (room) appends nothing.
- The WebClient `explore.look` target detail shows the identical block through the same appearance
  path, with no browser-side computation and no panel replacement.
- `get_display_value()` is hardened to treat a non-mapping `disguised_stats` record as "no
  disguise" (fall back to true values) instead of raising.
- The `disguised-stats-boundary` spec updates the three-consumer requirement: appearance rendering
  is now implemented through the `look <target>` displayed-stats block; appraisal items remain the
  forward-declared third consumer (deferral retained, consumer wording unchanged).
- Command-docs drift contract updated (the documented `look <target>` output gains the block).

## Capabilities

### New Capabilities
- `displayed-stats-view`: The five-key displayed combat-value block rendered through
  `get_display_value()`, appended to explicitly targeted look output identically across the text
  command and the WebClient look action, and never on room look or non-living targets.

### Modified Capabilities
- `disguised-stats-boundary`: The three-consumer requirement is updated — appearance rendering
  (`look`) is implemented through the `look <target>` displayed-stats block, and the appraisal-item
  deferral is retained; the consumer wording and the combat/resolution boundary stay unchanged.
- `localized-appearance`: The shared target-appearance layer additionally carries the
  displayed-stats block for living targets on every entry path (text 「看」, `at_look` hook, and
  `explore.look`), mirroring the existing affinity stage-line pattern.

## Impact

- `world/rules/displayed_stats.py` — new `display_stat_block()` renderer (new module; the
  `status_query.py` read model is frozen no-create and stays untouched).
- `world/rules/traits.py` — `get_display_value()` hardened against non-mapping disguise records;
  docstring consumer contract updated.
- `typeclasses/` — shared appearance path (`LivingEntity.get_display_desc`) appends the block for
  living targets (onboarding `at_look` detection unaffected).
- `web/webclient/actions/exploration_actions.py` — `explore.look` target detail gains the block via
  the shared path; no panel replacement.
- `docs/game/commands.md` / `command-reference.md` / `tests/test_command_docs.py` — updated for the
  documented `look <target>` output change.
- `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` — D2/§5.2 note updated to record the
  block as the implemented appearance-rendering consumer, per the project's amendment convention.
- No dependency, schema, or migration changes (project is unreleased; zero users).
