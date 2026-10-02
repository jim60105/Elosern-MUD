## Why

After the content slices, the companion preset extension, producers, import cards, generated-quest cards, and voice routing land, nothing yet proves at boot that the whole shipped roster is complete and coherent. The approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §5.2, §10, §11.2, §12, as amended by §13a) requires registry data and source coverage to be validated before activation — rejecting malformed or missing rows by profile/source key, never starting with a mix of new and silently missing content — and a recorded roster-wide editorial review. This gate is the precondition for the one-time cutover and is small enough to own separately from the cutover's transactional rewrite.

## What Changes

- Add `world/rules/npc_roster_validation.py`: derives the shipped NPC sources from the live registries (places, dialogue rows, guild ranks, preset companion declarations, the offline quest template pool, shipped import examples) and checks, naming the source and profile/preset on failure: inventory equality in both directions; every source resolves to a complete valid card (place host and examiner profiles, starting-companion declarations via the shared partner-preset derivation of `npc-persona-companion-profiles` with a maximum-length synthetic owner, template occupant cards, import example cards validated against the NPC target); every dialogue table is answered by exactly one profiled host; capability-aware voice coverage (every profile behind a scripted host authors a misunderstanding reply; every companion partner preset authors `speech_style` and a `greeting`); no orphan profile that no place, rank, or examiner reference uses (companion declarations reference presets, not profiles, so they cannot orphan a profile).
- Run it as a fail-loud boot step `npc_persona_roster_validation` after `state_reaction_rules` and before `sync_all`, so a server never starts with an incomplete roster.
- Replace the profile-registry inventory test's local source derivation with this module's function.
- Record the roster-wide editorial review in `docs/lore/npc-persona-roster-review.md` (cross-slice same-profession comparisons, coverage, and honest model-review status), and update `docs/development/adding-npcs.md` with the complete NPC authoring flow (profiles, slice ownership, references, inventory, voice lines, validation, the editor's no-regeneration note).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `npc-profile-registry` (introduced by `npc-persona-profile-registry`): ADDED requirement that the shipped roster is validated as complete before the game starts.

## Impact

- Code: `world/rules/npc_roster_validation.py` (new), `server/conf/at_server_startstop.py` (one boot step and `STARTUP_STEP_ORDER`), `world/lore/tests/test_npc_profiles.py` (derivation reuse).
- Tests: a new `world/rules/tests/test_npc_roster_validation.py` (rules shard registration), the startup-order guard test in `server/conf/tests/`.
- Docs: `docs/lore/npc-persona-roster-review.md` (new), `docs/development/adding-npcs.md` (authoring-flow sections), observability catalog (`startup_step` already covers the step; a failure uses the existing degrade path).

## Batch:

depends-on: npc-persona-content-altoria-lower
depends-on: npc-persona-content-altoria-trade
depends-on: npc-persona-content-altoria-guild
depends-on: npc-persona-content-altoria-upper
depends-on: npc-persona-content-ciaran-homes-a
depends-on: npc-persona-content-ciaran-homes-b
depends-on: npc-persona-companion-profiles
depends-on: npc-persona-host-examiner-producers
depends-on: npc-persona-import-cards
depends-on: npc-persona-generated-quest-cards
depends-on: npc-persona-dialogue-consumption
depends-on: npc-persona-dialogue-version-gate

Code-conflict notes: `server/conf/at_server_startstop.py` (`STARTUP_STEP_ORDER` and `at_server_start`) is also edited by `npc-persona-roster-cutover`, which lands after this change and inserts its own step; sequential, so no parallel conflict. `docs/development/adding-npcs.md` was edited by `npc-persona-import-cards` (import sections only); this change edits the authoring-flow sections. Every requirement here is satisfiable only after all listed changes, which is why it cannot run earlier; no placeholder profile or relaxed check may be used to make it pass sooner.
