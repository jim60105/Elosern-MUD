# Proposal

## Why

Every new character is created in the starting room 虛境 and is still there after
activation. The owner wants each subrace to begin in its own settlement, standing in
that settlement's gathering room. `START_LOCATION` cannot do this. The account
creates the character shell before anyone has picked a race, and the subrace is
only known when activation runs. So the move has to happen during activation.

## What Changes

- Activation (`world/rules/character_creation.py::activate_player_character`) resolves
  the start room with `subrace-start-locations`' resolver before any write. Inside the
  existing all-or-nothing transaction, it moves the character there without move hooks,
  sets `home` to that room and records the arrival in map knowledge. All of this happens
  before the preset starting companions are built, so the companions appear in the
  start room.
- The arrival effects of an ordinary move (the room's receive hook, arrival lore,
  encounter dispatch, the room look) run only after commit, as best-effort steps.
- On any failure, including the outer commit in `activate_draft`, the character is
  returned to its birth room without move hooks, even though 虛境 refuses character
  arrivals. Its `home` and map knowledge are restored as well.
- **BREAKING (spec)**: the "activation leaves the shell in 虛境 and records no map
  knowledge" scenarios are rewritten. The validator requires that their names stay, so
  their bodies now describe the start-room placement as the only move.
- Test seams. `world/tests/start_room_fixture.py` stubs start-room resolution for
  activation tests that do not test placement, and it is applied to every existing
  activation test module. The browser seed process stubs resolution so seeded characters
  stay in their seeded room. Creation browser runtimes materialize every start
  settlement.

Decided by the owner: 虛境 becomes a backstage holding room for creation-pending shells
only. Removing its gates is not part of this change; see the batch order below.

## Batch:

- depends-on: subrace-start-locations
- Batch order: `subrace-start-locations`, `subrace-start-settlements` (this change),
  `entrance-probe-fixtures`, `retire-limbo-city-gates`, `drop-settlement-city-gate-field`.
- Conflict notes:
  - `retire-limbo-city-gates` copies this change's `map-knowledge` requirement text, so
    this change must archive first.
  - Both changes edit `web/tests/browser/fixtures.py::journey_settlement_scope`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `player-character-creation`: activation moves the character to its subrace's start
  room and sets `home`. The two "no relocation" scenarios are rewritten (the validator
  keeps their names) so that the start-room placement is the only move. The rollback
  scenario now covers location, `home` and map knowledge.
- `webclient-character-creation-ui`: after web activation the character is in its
  subrace's start room, not in 虛境.
- `map-knowledge`: committed activation placement becomes an arrival-recording seam.

## Impact

- Code: `world/rules/character_creation.py`, `world/rules/creation_wizard.py`.
- Tests: new `world/tests/start_room_fixture.py`. The stub is added to every existing
  activation test module listed in tasks.md. Placement tests go in
  `test_activation_rollback.py`, `test_creation_wizard.py`,
  `test_starting_companions.py` and `test_fingerprint_activate.py`. Browser: `web/tests/browser/seed/runner.py`,
  `web/tests/browser/seed/npc_persona_fixture.py`, `web/tests/browser/fixtures.py`.
- Docs: `docs/development/adding-player-presets.md` (start location note).
- No human-reviewed document. Every requirement here is mechanism-testable.
