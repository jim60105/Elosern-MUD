# Proposal

## Why

Every new character is created in the starting room 虛境 and is still there after
activation. The owner wants each subrace to begin in its own settlement, standing in
that settlement's gathering room. `START_LOCATION` cannot do this. The account
creates the character shell before anyone has picked a race, and the subrace is
only known when activation runs. So the move has to happen during activation.

## What Changes

- New lore registry `world/lore/start_locations.py`. It maps every subrace key to
  exactly one start settlement, named by its anchor (location) identity. Import
  fails if a subrace has no row, a row names an unknown subrace, or a row is
  malformed.
- The static-reference closure (`world/maps/static_references.py`) gets a
  start-location family. Map-world adoption is rejected when a start anchor has no
  settlement placement in the candidate world. The start room is always that
  settlement's anchor room. It is found through the anchor placement, never through
  a coordinate or a dbref.
- New rules module `world/rules/start_location.py`. It resolves a subrace's start
  room from the current settlement graph and the materialized grid room.
- Activation (`world/rules/character_creation.py::activate_player_character`) resolves
  the start room before any write. Inside the existing all-or-nothing transaction it
  moves the character there, sets `home` to that room and records the arrival in map
  knowledge. All of this happens before the preset starting companions are built, so
  the companions appear in the start room. If activation fails, the character goes
  back to its birth room without move hooks and its `home` and map knowledge are
  restored. The same applies when the outer commit in `activate_draft` fails.
- **BREAKING (spec)**: the rules "activation leaves the shell in 虛境" and
  "activation records no map knowledge" are replaced.
- Test seams. `world/tests/start_room_fixture.py` stubs start-room resolution for
  activation tests that do not test placement. The synthetic data kit gets a
  start-location row. The browser seed process stubs resolution so seeded characters
  stay in their seeded room. Creation browser runtimes materialize every start
  settlement.

Decided by the owner: 虛境 becomes a backstage holding room for creation-pending shells
only. Out of scope here (follow-up changes in this batch): removing the 虛境 city-gate exits,
the gate `home` re-anchor and the `city_gate` document field.

## Batch:

- depends-on: elven-villages-eolas-fionnen (merged to master as e076e764; two of the
  start rows need its `elven_village_eolas` and `elven_village_fionnen` documents)
- Followed by `retire-limbo-city-gates` (depends on this change) and
  `drop-settlement-city-gate-field` (depends on `retire-limbo-city-gates`).
- Conflict notes: `retire-limbo-city-gates` edits `world/maps/static_references.py`,
  `world/tests/synthetic_data/*` and `web/tests/browser/fixtures.py`, which this
  change also edits. Apply this change first.

## Capabilities

### New Capabilities

- `character-start-location`: the per-subrace start-settlement registry, its
  validation at import and at map-world adoption, and resolving it to a room.

### Modified Capabilities

- `player-character-creation`: activation moves the character to its subrace's start
  room and sets `home`. The two "no relocation" scenarios are rewritten (the validator
  keeps their names) so that the start-room placement is the only move. The rollback
  scenario now covers location, `home` and map knowledge.
- `webclient-character-creation-ui`: after web activation the character is in its
  subrace's start room, not in 虛境.
- `map-knowledge`: committed activation placement becomes an arrival-recording seam.

## Impact

- Code: `world/lore/start_locations.py` (new), `world/lore/registry_index.py`,
  `world/rules/start_location.py` (new), `world/rules/character_creation.py`,
  `world/rules/creation_wizard.py`, `world/maps/static_references.py`.
- Tests: new `world/rules/tests/test_start_location.py` and
  `world/lore/tests/test_start_locations.py`. The new stub is added to every existing
  activation test module (listed in tasks.md). Synthetic kit: `data_characters.py`,
  `targets.py`, `__init__.py`. Browser: `web/tests/browser/seed/runner.py`,
  `web/tests/browser/seed/npc_persona_fixture.py`, `web/tests/browser/fixtures.py`.
- Docs: `docs/development/adding-player-presets.md` (start location note),
  `world/rules/AGENTS.md` module table.
- No human-reviewed document. Every requirement here is mechanism-testable.
