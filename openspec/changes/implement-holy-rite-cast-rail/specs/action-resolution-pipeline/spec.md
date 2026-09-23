# action-resolution-pipeline — delta for implement-holy-rite-cast-rail

## ADDED Requirements

### Requirement: The church-rite effect handlers reject with four named stable reasons
`world/rules/action.py`'s `RejectReason` SHALL declare `RITE_NOT_ENROLLED`, `RITE_COOLDOWN_ACTIVE`,
`RITE_OUTSIDE_VENUE`, and `RITE_ALREADY_SHELTERED`, and `world/rules/player_messages.py` SHALL
supply each one's Traditional Chinese player-facing line.
The two holy-rite effect handlers SHALL raise `RejectedAction` with these reasons during step-5
staging, before any `PendingEffect` is staged: `RITE_NOT_ENROLLED` when the actor's `db.church`
ledger is absent, `RITE_COOLDOWN_ACTIVE` when `rite_martial_blessing`'s ledger cooldown stamp is
inside its rulebook cooldown window, `RITE_OUTSIDE_VENUE` when `rite_shelter` resolves outside a
church-flagged place, and `RITE_ALREADY_SHELTERED` when `rite_shelter` resolves with the current
day-block already marked. Each rejection SHALL leave every surface byte-identical and advance no
clock, matching the pipeline's existing zero-write rejection promise. These gates live in the
handlers (step 5), not the shared preview: `world/rules/action_preview.py` SHALL keep mirroring only
the pre-staging steps, exactly as it does for every other handler-raised gate.

#### Scenario: An unenrolled caster is refused with the named reason and zero writes
- **WHEN** an entity with no `db.church` ledger casts `rite_martial_blessing` out of combat
- **THEN** `resolve()` returns `outcome == "rejected"` with
  `reason == RejectReason.RITE_NOT_ENROLLED`, and traits, buffs, and the clock are byte-identical

#### Scenario: A cooled-down blessing is refused before staging
- **WHEN** an enrolled holder casts `rite_martial_blessing` while her ledger cooldown stamp is inside
  the `church.yaml` cooldown window
- **THEN** the result carries `RejectReason.RITE_COOLDOWN_ACTIVE` and stages nothing — no buff, no
  re-stamped ledger, no clock access

#### Scenario: Shelter outside a sanctuary venue is refused
- **WHEN** an enrolled holder casts `rite_shelter` in a place without the `church` flag
- **THEN** the result carries `RejectReason.RITE_OUTSIDE_VENUE` and no trait or ledger state moves

#### Scenario: The second same-day shelter is refused
- **WHEN** an enrolled holder already marked this day's shelter block and casts `rite_shelter` again
  inside the venue
- **THEN** the result carries `RejectReason.RITE_ALREADY_SHELTERED` and hp, sp, and the ledger are
  byte-identical

#### Scenario: Every rite rejection renders a fixed zh-TW line
- **WHEN** each of the four reasons is rendered through the player-message surface
- **THEN** each maps to its configured Traditional Chinese line, with no raw enum or exception text
  reaching the player
