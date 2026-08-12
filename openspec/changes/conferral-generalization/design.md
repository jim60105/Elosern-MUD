## Context

`world/skills/handler.py`'s `ConferredSkillGrant(source_key, skill_key, trait_keys, scale)` and
`_handle_confer_skill_partial` in `action.py` (requiring `confer_skill_key`/`confer_scale`/
`confer_trait_keys` event context) currently only make sense for `stat_multiply` — `trait_keys` is a
`stat_multiply`-specific concept. This landed correctly for 統御術's one tested narrative case
(伊洛希雅 conferring body-enhancement to 薇歐蕾特) but the design doc calls for generalizing before more
conferrable effect types exist, per D6.

## Goals / Non-Goals

**Goals:**
- Any continuous-valued effect (currently: `stat_multiply` via `effective_value`, and whatever
  `skill-owned-rule-condition` lands via `combat_modifiers.yaml`) becomes conferrable at a fractional
  `scale` through one shared grant record shape.
- Gate-type effects are structurally excluded, not just excluded by convention/documentation.

**Non-Goals:**
- Does not change `growth_rate`'s existing conferral path (`confer_growth_rate`/
  `grant_conferred_growth_rate`) — that already works and is out of scope; this change only touches
  `ConferredSkillGrant`/`confer_skill_partial`, the mechanism `dominion_art` itself uses.
- Does not add conferral of `heal`, `damage`, `movement`, or `divine_mystery` effects — none of these
  are continuous-valued ongoing quantities in the sense 統御術's own flavor text implies ("一部分自身
  技能的效果" reads as an ongoing partial share, not a one-shot cast borrowed from someone else).

## Decisions

- **Drop `trait_keys` from `ConferredSkillGrant`.** It was only ever a cache of what
  `SKILL_REGISTRY[skill_key]`'s own `stat_multiply` effects already state. Once effects are typed
  (`skill-effects-typed-model`), any consumer can derive "which traits does this skill's effect touch"
  directly from `parsed_effects` — storing it a second time in the grant record is redundant state that
  could drift from the source skill's actual definition.
- **Exclusion is structural (effect class), not a hardcoded skill-key blocklist.** `parsed_effects`
  already distinguishes `StatMultiplyEffect`/`RuleTableEffect`-shaped classes (continuous) from
  `ElementMasteryEffect`/`SexualMasteryEffect`/gate-type classes (binary). The conferral-resolution
  helper pattern-matches on class, not on a maintained list of forbidden skill keys — this means a
  *future* gate-type effect class is automatically excluded without anyone remembering to update a
  blocklist.
- **Each consumer (`effective_value`, the `skill_owned` context builder) independently checks
  `conferred_grants()`**, rather than a single central "resolve all conferred effects" function — this
  matches the existing pattern where `effective_value` already does its own conferral lookup inline,
  and avoids introducing a new cross-cutting resolution pass this early.

## Risks / Trade-offs

- [Risk] Dropping `trait_keys` from the stored grant shape is a breaking change to any existing
  `ConferredSkillGrant` data (though none exists in a running save yet — zero users). → Mitigation:
  no migration needed per project policy; task list includes updating the one existing test fixture
  that constructs `ConferredSkillGrant` with `trait_keys`.
- [Risk] Structural exclusion by class requires every future effect class to be correctly categorized
  as continuous vs. gate-type at the point it's added to `effects.py`, or conferral could silently
  accept a nonsensical grant. → Mitigation: `skill-effects-typed-model`'s dispatch table is the single
  place new effect classes get added; task list for *that* change (already landed by the time this one
  starts) is not retroactively updated, but this change's own tests assert the exclusion against every
  currently-known gate-type class explicitly, so a regression is caught even without a structural
  guarantee at the type-system level.

## Migration Plan

No runtime data migration (zero users). Lands after `skill-effects-typed-model` and
`skill-owned-rule-condition`.

## Open Questions

None.
