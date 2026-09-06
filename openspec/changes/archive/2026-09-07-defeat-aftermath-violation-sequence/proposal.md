# Proposal: DA4 — defeat-aftermath-violation-sequence

Change ID: **DA4** (parent design §8 archive order).

## Why

The owner's approved design makes adult content the core of the defeat
fantasy: when the winning monsters go into the fight aroused past their
archetype threshold, they violate the downed player, attempt by attempt,
each attempt resisted by the shipped d100 contest, each attempt spending
world time and rewriting sexual state. Without this layer,
`defeat-aftermath-core` is a sterile PG loop; with it, the emergent
combat-depth promise closes the loop — a monster the player himself aroused
mid-fight wins more virulently. Companion victims are a deliberate later
extension (`defeat-aftermath-companion-victims`); this change ships the
complete mechanics against the player pool alone.

## What Changes

- **Per-archetype monster sexual behavior** lands: the design-doc §6.4 seam
  (this change owns it) — `rulebook/defeat_aftermath.yaml` gains an
  archetype-keyed section (victory arousal delta, violation threshold,
  attempt cap, per-attempt deltas/duration), validated section-owned at
  load. Monster `SexualState` mount semantics are NOT touched: monsters
  keep the shipped floor baseline with `shame` pinned at 無; the archetype
  data lives entirely in the defeat registry, its only consumer.
- **Victory arousal table**: every living winner of a hostile defeat gains
  archetype-keyed pleasure points at settlement, on top of whatever the
  fight already raised (the player's own sexual-magic casts, catalog acts
  the monster used mid-fight), clamped by existing counter bounds.
- **Violation sequence** registers into the core's `DEFEAT_ADULT_SCENES`
  guarded hook (the flag itself belongs to the core change; this change
  adds no settings): for each living winner whose post-victory arousal ≥
  its archetype threshold, up to the archetype's attempt cap — each attempt
  targets the player, rolls one resist contest through the existing pure
  `resist_verdict(actor, resister, *, rng)`
  (`world/rules/sexual_resist.py`) with the state-derived roll injected,
  applies the attempt's declared state deltas + symmetric counter credits
  (per the shared convention from `sexual-counter-symmetric-crediting`),
  and advances the world clock by the attempt's declared duration. **The
  first successful resistance cancels that violator's remaining attempts**;
  a sequence where zero attempts landed is the PG variant.
- **State-derived dice, no RNG state**: every d100 is a pure function of
  durable record state (session id + violator + victim + attempt index).
  There is no seeded stream to persist — `roll_d100` is a stateless Evennia
  dice wrapper and `CombatSessionRecord` stores no seed — so a rolled-back
  settlement retried through the existing recovery fallback re-derives the
  identical sequence for free.
- **Digest handoff**: the sequence returns an in-memory, per-participant
  outcome object (selected/landed/resisted counts, climax delta,
  zero-landed flag) to the settlement call graph; `defeat-aftermath-digest-narrative`
  consumes it directly. Nothing new is persisted.
- **EventLog vocabulary**: new open-kind strings `violation_attempt`,
  `violation_resisted`, `violation_act` (declared vocabulary addition with
  zh-tw template lines authored here — `EventEntry.kind` is an open field,
  no schema change), ordered between the core's `defeat_settle` and
  `violator_depart`.

## Capabilities

### New Capabilities

- `defeat-aftermath-violation-sequence`: victory arousal, archetype
  threshold/cap/delta registry, state-derived sequence dice, per-attempt
  resist contest via `resist_verdict`, per-attempt clock advance and
  state/counter writes, first-resistance violator stop, zero-landed PG
  variant, and the in-memory digest outcome handoff.

### Modified Capabilities

_None — the core's atomic-unit delta already enumerates "the adult phases
contributed by later changes", and the hook guard is core-owned. (No
`sexual-state-handler` change: the per-archetype seam is defeat-registry
data, not a SexualState mount-semantics change — the pinned-shame and
floor-baseline requirements stay verbatim true.)_

## Impact

- `world/rules/defeat_aftermath.py` (sequence engine + hook registration
  beside the core writer),
  `world/rules/rulebook/defeat_aftermath.yaml` (archetype rows + this
  section's loader validator), `world/rules/state_derived_roll.py` (new
  pure derivation helper), `world/rules/player_messages.py` (violation
  template lines), `world/lore/monsters.py` archetype-key validation at
  rulebook load.
- `world/rules/action.py` is NOT edited — `resist_verdict` is already the
  extracted pure contest (`sexual_resist.py`), called as-is with the victim
  as `resister` and an injected `rng`.
- Tests: new `world/rules/tests/test_defeat_aftermath_violation.py`;
  existing `test_sexual_state.py` monster-baseline tests stay green
  unmodified; shard manifest updated same change.
- **Depends on**: `defeat-aftermath-core` (the hook + transaction) and
  `sexual-counter-symmetric-crediting` (the shared crediting convention).
  **Blocks**: `defeat-aftermath-companion-victims`,
  `defeat-aftermath-digest-narrative`.
