## Why

The original scope of this change was the one-time, exclusive, transactional in-place replacement of every pre-persona NPC database described in `docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §6.2. The user has since ordered (2026-10-02) that no database migration ships for this design set: existing development databases are disposable, will be destroyed, and will be re-initialized instead. The project has no released users, every production creation path already materializes complete persona cards with the current content-generation marker (`npc-persona-host-examiner-producers`, `npc-persona-companion-profiles`, `npc-persona-import-cards`, `npc-persona-generated-quest-cards`), and the boot roster validation (`npc-persona-roster-validation`) already refuses to start a world whose shipped roster is incomplete. A bespoke plan/apply/suspend boot mechanism would therefore be migration infrastructure built solely to migrate throwaway data — exactly what the repository's no-migrations default forbids — while its only enforcement value (restore fails closed on pre-amendment payloads) already exists via the strict codec from `npc-persona-generated-quest-cards`.

This change replaces the in-place cutover with the supported database lifecycle: amend the design document to supersede §6.2, document the destroy-and-reinitialize runbook, and pin the two behaviors the replacement relies on with regression tests.

## What Changes

- **Supersede the in-place cutover** in the design document with a dated, user-ordered amendment clause (the §13a pattern): pre-amendment databases are unsupported and are replaced by destroy-and-reinitialize, not migrated. The cutover mechanism (writer suspension, `plan_cutover()`/`apply_cutover()`, the `npc_persona_cutover` boot step, and its three events) is NOT implemented and no code for it exists on any branch.
- **Add a developer database reset runbook** under `docs/development/`: stop the server, remove the SQLite database file named by the project settings, run `evennia migrate`, start the server so startup syncs and NPC producers materialize a fully marked roster, and confirm via the `startup_step` and roster-validation events. Include the retained test database (`server/db/evennia-test.sqlite3`) and the persistent container volume.
- **Pin the two relied-upon behaviors with tests** (new module `world/rules/tests/test_npc_persona_fresh_bootstrap.py`, rules shard): a freshly synchronized database yields an NPC family in which every instance carries the current content-generation marker and a valid complete card without any rewrite step, and a frozen pre-amendment generated-quest payload fixture (captured with `git show` from before `npc-persona-generated-quest-cards`) fails restore validation deterministically, proving no legacy compatibility decoder exists.
- **Amend design doc §6.2/§12.2** so the shipped record matches: change 20 is a database-lifecycle change, not a migration.

## Capabilities

### New Capabilities

- `npc-persona-cutover`: persona-content adoption at the database boundary — fresh initialization produces the complete marked roster with no rewrite step, pre-amendment databases fail closed and are replaced by a documented destroy-and-reinitialize, and no runtime legacy decoder exists.

### Modified Capabilities

None. The foundation's writer contract, the roster-validation boot gate, and the strict quest-payload codec keep their existing requirements; this change adds no writer suspension and no boot step.

## Impact

- Code: none. No new production module, no boot-step change, no observability catalog rows.
- Docs: `docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` §6.2 amendment (dated, user-ordered); new `docs/development/database-reset.md` runbook.
- Tests: `world/rules/tests/test_npc_persona_fresh_bootstrap.py` (rules shard registration) with a frozen synthetic pre-amendment payload fixture; `tools.spec_traceability` coverage for the new capability's requirements.
- Data: pre-amendment development databases (including `server/db/evennia-test.sqlite3` and the container's persistent DB volume) are deleted per the runbook, never read by game code.

## Batch:

depends-on: npc-persona-roster-validation
depends-on: npc-persona-generated-quest-cards
depends-on: npc-persona-companion-profiles
depends-on: npc-persona-host-examiner-producers
depends-on: npc-persona-import-cards
depends-on: npc-persona-offline-bundles

Code-conflict notes: touches no shared code file. The design document is edited by no other active change; `at_server_startstop.py` is NOT touched (the roster-validation step from change 19 stays where it is). Must land after `npc-persona-generated-quest-cards`, whose strict decoder is the fail-closed enforcement that makes destroy-and-reinitialize the only supported path for pre-amendment databases.
