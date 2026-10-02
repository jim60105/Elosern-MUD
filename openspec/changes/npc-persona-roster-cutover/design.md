## Context

See proposal.md for the user-ordered scope reversal (2026-10-02: no database migration; existing databases are destroyed and re-initialized). Facts this plan relies on: every production NPC creation path already writes a complete compact card plus the current content-generation marker at creation time (`npc-persona-host-examiner-producers`, `npc-persona-companion-profiles`, `npc-persona-import-cards`, `npc-persona-generated-quest-cards`); `npc-persona-roster-validation` fails the boot loudly when the shipped roster is incomplete; the generated-quest store decodes payloads through the strict codec from `npc-persona-generated-quest-cards`, which rejects occupant characterizations that are not complete cards; the project's stated default is no backward-compatibility layers or data migrations because there are no released users; the retained test database is `server/db/evennia-test.sqlite3` and the container image mounts a persistent SQLite volume.

## Goals / Non-Goals

**Goals:** the persona design set reaches its done-state without shipping migration code; a fresh database is demonstrably born with the complete marked roster; pre-amendment databases fail closed with a named error and have a documented, supported destroy-and-reinitialize path; the design document's shipped record matches reality.

**Non-Goals:** any cutover mechanism (suspension guard, plan/apply phases, boot step, cutover events); a legacy payload decoder; general migration infrastructure; changes to the roster-validation boot gate, the strict codec, or any writer contract; touching any existing database file as part of implementation (the actual developer-database deletion is an operator action ordered outside this change's code).

## Decisions

### D1. Delete the cutover mechanism rather than ship it

The §6.2 in-place cutover exists only to move pre-amendment data forward. Under the user's destroy-and-reinitialize order, that data class is unsupported by definition, so the mechanism's plan/apply/suspend code, its `npc_persona_cutover` boot step, and its three observability events are not implemented at all — no dead code, no dormant boot step, no catalog rows. Enforcement that nobody boots against pre-amendment payloads is already provided for free: the strict codec fails restore deterministically. The repository's no-migrations default then becomes the active rule instead of an exception to it.

### D2. Supersede design §6.2 with a dated amendment clause

The design document gains a dated, user-ordered amendment in the §13a style (§13b) stating: the §6.2 one-time in-place cutover is superseded by supported database lifecycle — pre-amendment databases are destroyed and re-initialized per the developer runbook, and `npc-persona-roster-cutover` delivers the fresh-bootstrap guarantees and the runbook instead of a migration. §6.2's heading gets a pointer to the amendment; §12.2's row 20 scope text is corrected the same way. The original §6.2 body is kept as historical rationale under the amendment, exactly as §13 keeps pre-amendment clauses.

### D3. Runbook is the operator contract

`docs/development/database-reset.md` documents the full procedure: stop the server; delete the SQLite file named by the server settings (dev default `server/db/evennia.db`); `uv run --locked evennia migrate`; start the server; verify the `startup_step` events complete, `npc_persona_roster_validation` passes, and the NPC family is fully marked. It names the retained test database (`server/db/evennia-test.sqlite3` — same removal procedure, or drop `--keepdb` per AGENTS.md) and the container persistent volume, and it states explicitly that deleting the database also deletes player characters, progress, and generated quests — intended for pre-release development use only.

### D4. Two pinned behaviors plus a docs contract, one test module

`world/rules/tests/test_npc_persona_fresh_bootstrap.py` (rules shard) pins what the replacement relies on:

1. **Fresh bootstrap is born complete:** after startup syncs against a synchronized test database, every NPC-family instance carries the current content-generation marker and a contract-valid complete card, with no rewrite step run — proving producers alone suffice.
2. **Pre-amendment payloads fail closed:** a pre-amendment-shape occupant payload (old optional three-field `persona` plus `background`, shape hand-copied from the pre-change durable schema via `git show` of the codec at the commit before `npc-persona-generated-quest-cards`) is rejected by the strict restore path with a named validation failure — proving no compatibility decoder exists. The fixture is file-local synthetic data in the pre-change shape, not shipped lore, so it needs no data-freeze registration.
3. **Runbook contract:** the reset runbook exists and names the migrate step and the retained test database path, guarding the operator contract the same way `tests/test_command_docs.py` guards player docs.

The first two assertions are behavior; none of them pins prose. The module is registered in exactly one `.github/evennia-shards.json` shard and its requirements carry literal `covers_requirement` IDs.

## Risks / Tradeoffs

- [A developer boots with an old database and hits a hard restore failure] → intended fail-closed behavior; the runbook is the named remedy, linked from the failure's operational event context; single-player pre-release scale makes loss acceptable and the user ordered exactly this.
- [The design doc's §6.2 narrative still describes a cutover] → D2's amendment clause is the shipped-of-record supersession; §12.2's table row is corrected in the same edit so no reader follows a stale instruction.
- [A future team wants in-place migration] → explicitly out of scope; nothing built here blocks writing one as a new change when there are released users to protect.
