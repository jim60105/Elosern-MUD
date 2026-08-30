# Design: magic-xp-engine-retirement

## Context

Predecessor `magic-power-static-rename` made `magic_power` a fourth static trait; the
XP engine (`accrue_magic_study`, `grant_combat_kill_xp`, `magic_xp`) still runs
against it, and the element-effective numeric cast gate still consults it. This
change executes design §7's deletion table down to the point where `magic_power` has
zero writers, then holds a deliberately thin interim until `use-driven-skill-lineage`
lands `can_use_skill` (D5). The design doc §13 Change B owns this scope.

## Goals / Non-Goals

- Goals: zero magic-XP state and writers remain; cast gate reduced to ownership +
  MP affordability; stage tuple position preserved under the new name; the deletion
  leaves every EventLog/quest consumer byte-stable.
- Non-Goals: no practice-settlement growth (owned by `declared-practice-skip`), no
  lineage graph or `can_use_skill` (owned by `use-driven-skill-lineage`), no freeform
  ladder re-anchor (C), no mastery-skill deletion (only their effect strings change).

## Decisions

### DB1: `practice_settlement` is an inline zero-growth stage, not a lazy seam
The self-arming lazy import existed only because `accrue_magic_study` lived in a
change that landed later. With the target deleted, `world/rules/clock.py` keeps the
tuple slot (`("gauge_regen", "buff_ticks", "sexual_decay", "practice_settlement", …)`)
with an inline no-op stage function documented as the `declared-practice-skip`
insertion point. The COMBAT-source skip gate stays (composition contract survives;
the eventual writer must never run in combat).

### DB2: interim cast gate = ownership + MP affordability
`ActionResolver.preflight`/`resolve` drop the elemental tier rejection entirely (the
whole `element-mastery-cast-gate` requirement is REMOVED, not narrowed); preview
drops spell-tier eligibility and its gate scenarios; the monster/companion policy
proposes the first affordable resolver-backed damage skill. `element_affinity_multiplier`
survives unchanged as a pure multiplier (C re-anchors its consumption site). MP cost
checks are untouched, so unaffordable high-tier spells still fail naturally.

### DB3: defeat credit keeps attribution, loses XP
`world/rules/upkeep.py` keeps `source_pk` attribution (defeat EventLogs and quest
planners need it) but no longer stages `grant_combat_kill_xp()`. The action
pipeline's deferred kill-XP staging exception disappears: `action.py` reverts to
zero combat-shape conditionals except the `usable_out_of_combat` gate. Requirement
titles in `combat-upkeep-settlement` are kept verbatim (traceability IDs are live);
their bodies/scenarios lose XP wording and the XP assertions become zero-write
assertions.

### DB4: `magic_xp` leaves every durable surface at once
Snapshot registries in `action.py`, `clock.py`, `cast_settlement.py` and the creation
activation list drop the key; `_stored_magic_xp` and its finite/non-negative
validation die with it. No attribute-scrub migration (unreleased, zero users).

### DB5: mastery skills keep identity, shed the rank effect
The `element_mastery_rank` typed effect class is deleted; `parse_effect` fails closed
on the prefix. All eight `<element>_mastery` rows (one per element) switch to
`effects=["passive_trait:element_mastery"]`, the established inert-flavor form.
`sexual_magic_mastery` is explicitly NOT touched: design §7 exempts it (its ladder is
SEXUAL_ACT_REGISTRY-gated). Freeform entitlement keys on mastery **ownership**
(`freeform_scales_for`) and is untouched by this change.

### DB6: capability retirement is total
`magic-level-progression` loses all six requirements (its two requirements the
predecessor renamed/modified are removed from that post-A state). The
`growth_rate_multiplier()` pull path (buff-handler-integration) survives with an
updated docstring contract: currently unconsumed, re-consumed by C's practice-XP
formula — the tick stays a documented no-op so nothing double-applies.

## Risks / Trade-offs

- Interim window has no numeric cast gate → high-tier spells castable at creation.
  Accepted: C lands in batch [C ∥ F] before any release; design §13 states the
  ungated interim never ships.
- Renaming the two `settlement-stage-order` requirement titles changes
  traceability IDs; the post-sync re-pin task covers it.

## Migration

Not applicable — unreleased, zero users, no save scrub (AGENTS.md). Tests are
re-pinned in the same change.

## Open Questions

(None.)
