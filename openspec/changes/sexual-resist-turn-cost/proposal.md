## Why

`sexual-resist-contest` (`B6a`, this document set's sibling proposal) ships `resist_verdict()` as a
pure function with **no production caller** — its own proposal explicitly states "this proposal has
no caller until `sexual-resist-turn-cost` lands." The approved design
(`docs/superpowers/specs/2026-08-15-sexual-act-resolution-design.md` §5, "Turn Cost and Affinity
Consequence", proposal `B6b` in that document set's implementation sequence) requires that only a
*forced* act — one where the target attempted to resist and failed — costs the target's affinity
toward the actor, while a target who complies (by choice or by `auto_comply`) or successfully
resists never loses affinity. Nothing today can apply that consequence, because nothing today knows
a resist was even attempted: `resist_verdict()`'s three-way outcome (comply / resisted / forced) has
no path into the game's one existing affinity writer, `world/rules/affinity.py::apply_affinity_change`.

This proposal wires that consequence into live combat resolution, reusing the exact scan-and-penalize
pattern the already-shipped friendly-fire mechanic established, so a forced sexual act on a companion
NPC can — like a friendly-fire hit — drive the companion's affinity below `invite_threshold` and
trigger the existing party auto-leave.

## What Changes

- Add `AffinitySource.SEXUAL_FORCED` to `world/rules/affinity.py`'s closed source enum.
- Add `sexual_forced_penalty` to `world/rules/rulebook/affinity.yaml` and its loader/validator in
  `world/rules/affinity_config.py`, mirroring the existing `friendly_fire_penalty_per_hit` field
  exactly (same validation shape, same closed `_TOP_LEVEL_FIELDS` set extended by one key). **This
  extends this proposal's file ownership beyond the overview document's original table**
  (`combat_session.py`, `affinity.py` only) to include `affinity_config.py` and `affinity.yaml`; see
  design.md's amendment note for why a dedicated, independently-tunable penalty is preferred over
  reusing `friendly_fire_penalty_per_hit`'s existing value, and `docs/superpowers/specs/
  2026-08-15-sexual-act-system-overview-design.md` is updated in the same change to reflect this
  correction.
- Add `world/rules/combat_session.py::_scan_sexual_coercion(actor, battlefield, logs) ->
  tuple[str, ...]`, structurally mirroring the shipped `_scan_friendly_fire` exactly: scans the
  round's resolved `EventLog`s for entries of a new, documented contract kind (`"sexual_resist"`,
  `data={"resisted": bool, "auto_comply": bool, "roll": int | None}`), and for every entry where
  `resisted is False and auto_comply is False` (a target who tried to resist and failed — "forced"),
  applies `sexual_forced_penalty` through `apply_affinity_change(target, actor,
  AffinitySource.SEXUAL_FORCED, -penalty)` inside the same nested-transaction, rollback-covered
  pattern `_scan_friendly_fire` already uses. A `resisted=False, auto_comply=True` entry (compliance,
  rolled or automatic) and a `resisted=True` entry (a successful refusal) both apply no penalty.
- Wire `_scan_sexual_coercion` into `submit_player_action` immediately beside the existing
  `_scan_friendly_fire` call, inside the same shared outer transaction (fix-combat-settlement-recovery
  D1's documented seam), combining both scans' auto-leave notification lines.
- Broaden `_snapshot_party_surfaces`/`_restore_round_touched`'s `relations_data` coverage from
  party-companion NPCs only to **every `NPC` present in the battlefield roster**, because a forced
  sexual act can target any present NPC (out-of-combat `SINGLE` targeting already permits "anyone
  present", and the in-combat case is not restricted to a player's own party by anything in the
  targeting or resist-contest design) — not only a declared companion, which is friendly-fire's own
  narrower, correct-for-friendly-fire scope. Without this, a rolled-back round involving a
  non-companion NPC resister would leave that NPC's `relations_data` idmapper cache holding a
  post-write value the database rollback already discarded.
- Document, as a forward-declared contract (matching the precedent `climax-settlement`'s design.md
  set for `stage_climax_extension()`), the exact `EventEntry` shape `sexual-act-effects` (`B4`/`B5`,
  not yet implemented) must emit for every resistible participant so this proposal's scan can react
  to it. This proposal adds no caller of `resist_verdict()` itself and mutates no `SexualState`
  field — it only consumes the contract's output.

## Capabilities

### New Capabilities
- `sexual-resist-turn-cost`: the affinity consequence of a resisted or forced sexual act during
  active combat — a new `AffinitySource`, a dedicated penalty constant, and the post-round scan that
  applies it exactly once per forced act, symmetric with the shipped friendly-fire mechanic.

### Modified Capabilities
- `affinity-system`: the sole-writer requirement's closed source set gains `sexual_forced`, mirroring
  exactly how the archived `affinity-friendly-fire` change added `friendly_fire` to the same closed
  set — no behavior change for any existing source. (`player-combat-session`'s shipped requirements
  about round settlement are unaffected in their observable contract, since this proposal adds a new,
  independent post-round side effect rather than altering any existing one; that capability is not
  listed here because it carries no delta spec.)

## Impact

- **New capability spec:** `openspec/specs/sexual-resist-turn-cost/` (this change).
- **Modified files:** `world/rules/affinity.py` (new `AffinitySource` member),
  `world/rules/affinity_config.py` and `world/rules/rulebook/affinity.yaml` (new
  `sexual_forced_penalty` field), `world/rules/combat_session.py` (`_scan_sexual_coercion`, its
  wiring into `submit_player_action`, and the broadened relations-snapshot scope).
- **Reads (no changes) from:** `world/rules/sexual_resist.py`'s `ResistVerdict` shape (`B6a`, for the
  documented `data` contract's field names only — this proposal does not call `resist_verdict()` or
  import from `sexual_resist.py`), `world/rules/event_log.py` (`EventEntry`), `typeclasses/npcs.py`
  (`NPC`).
- **Explicitly deferred, not silently dropped:** the identical out-of-combat consequence
  (`world/rules/cast_settlement.py` has no equivalent post-cast scan call site today, and neither it
  nor `commands/action.py` is in this proposal's file ownership). The approved design states "the SP
  costs, state transitions, and affinity consequences are otherwise identical" out of combat; this
  proposal ships only the in-combat half and names the out-of-combat half as a follow-up proposal's
  scope in design.md's Non-Goals, rather than expanding this proposal past a one-day implementation
  or silently leaving the gap undocumented.
- **Dependencies:** `sexual-resist-contest` (`B6a`, for the `ResistVerdict`/EventLog-contract field
  names this proposal's scan matches against) and `sexual-act-effects` (`B4`/`B5`, not yet shipped —
  the party that will actually emit the `"sexual_resist"`-kind `EventEntry` this proposal consumes;
  until it lands, `_scan_sexual_coercion` is exercised only by this proposal's own tests, exactly as
  `stage_climax_extension()` was exercised only by `climax-settlement`'s own tests before a caller
  existed).
