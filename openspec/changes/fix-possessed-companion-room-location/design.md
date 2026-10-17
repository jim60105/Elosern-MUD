# Design

## Context

See `proposal.md` for the verified defect and scope. The supplied reproduction is accepted evidence, not an investigation to repeat. A real session produced `RELEASED char1 Room npc None ... party [10]`, then ordinary follow left the companion at `None`. A second probe established the same outcome for `release_for_party_change`.

The architectural authority is `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` §3.1, with the approved possession-specific decisions in `docs/superpowers/specs/2026-09-05-companion-possession-design.md` D1/D3/D4/D8. D4 in the latter document preserves the owner's physical body. The engine design's own D4 concerns the clock. Neither permits a new teleport mechanic. State mutation belongs to deterministic owners; `world/ai/` remains read-only/proposal-only.

Today `release_possession` calls `_unmount_cmdset`, then `_unpuppet`, then clears the owner and companion bindings (`world/rules/possession.py:717-727`). Evennia's `DefaultCharacter.at_post_unpuppet` stashes the last-session character by saving `db.prelogout_location` and assigning `location = None`. NPCs inherit that behavior through `LivingEntity`. The existing `PlayerCharacter.at_post_unpuppet` guard restores the owner's location during entry and continues to render its body as 呆立入神.

## Goals / Non-Goals

**Goals**

Preserve the companion's actual occupied room across the canonical `handback` and `party_change` release ladder, including refusal, retry, and transaction compensation. Publish handback presentation only after room truth has been restored. Reuse the existing party and possession gates.

**Non-Goals**

Disconnect/link-dead location recovery, global NPC logout behavior, partial/orphan binding repair, already-stranded object repair, reunion teleportation, and changes to party removal policy are excluded. No command key/alias/syntax/availability or payload schema changes are planned. No compatibility layer or migration is needed in this unreleased project.

## Decisions

### 1. Restore in the rules writer, with no new typeclass override

Change `world/rules/possession.py::_unpuppet` on the normal handback path shared by both release reasons. Snapshot the companion's occupied location before any session unpuppet. After each `account.unpuppet_object(session)` attempt, restore that location directly when the hook has stashed it, before owner re-puppeting or `synchronize_session`. Use a `finally` boundary around that attempt so a hook that stashes and then raises cannot leave location restoration skipped. Keep the existing exception diagnostics and verified return ladder.

A direct location assignment reverses framework bookkeeping; `move_to` would add an unrelated world traversal and movement hooks. Only a non-null snapshot is a restoration source. Do not guess a room from the owner's location, home, or stale logout metadata, and do not broaden this into recovery of pre-existing off-grid objects. Multiple sessions must use the original snapshot across the loop; restoring before each owner handback also covers the last-session stash without changing sequencing.

Alternative considered, an NPC or `LivingEntity.at_post_unpuppet` guard symmetric to D4, would depend on `npc.db.possessed_by` still being set when `super()` stashes it. That condition holds today because `release_possession` clears bindings after `_unpuppet`; moving that clear earlier would silently disable the guard. A living-entity override would also affect player/monster and unrelated lifecycle paths. The writer-side choice keeps this scoped correction, rollback, and success logging under the deterministic transition owner. It does not rely on the binding being present inside a typeclass hook. Preserve the existing binding-clear order anyway, since failed handback must retain the possession and player-body semantics depend on it.

Leave `typeclasses/entities.py`, `typeclasses/npcs.py`, `typeclasses/characters.py`, `typeclasses/accounts.py`, and `commands/possess.py` unchanged. In particular, do not wire release cleanup into any unpuppet hook or edit the player's D4 guard.

### 2. Remove logout residuals and compensate their exact pre-release state

Evennia also writes `prelogout_location` during `at_pre_puppet`, so restoring `location` alone leaves a stale NPC logout restore target. For a successful occupied normal release, remove the companion's `prelogout_location` Attribute after its unpuppet bookkeeping. Remove `prelog_location` too if present, without introducing it or consulting it as a fallback. The installed Evennia source uses `prelogout_location`; no checked project usage of `prelog_location` was found. The latter removal is bounded residual cleanup, not an alias or compatibility path. Do not clear the owner's metadata or change ordinary player logout.

Extend `world/rules/possession.py::snapshot_party_control` and `restore_party_control` to cover the companion's location and the presence/value of both logout Attributes. The latter must restore these cached and durable surfaces as well as the existing bindings, locks, cmdset, and session control when release or an outer party/escort transaction fails. Restore the occupied location before re-puppeting the companion during compensation, then re-establish the exact saved Attribute presence/values after puppet hooks, which can write `prelogout_location` again. Keep the existing fresh-epoch recovery behavior. No successful release event is emitted for a failed release.

`release_possession` already invokes these compensation helpers; adjust its successful boundary event context as described below. `release_for_party_change` keeps delegating with `reason="party_change"`. Its callers need no API change.

### 3. Membership preservation describes the release boundary

The new requirement adds presence guarantees without overriding `companion-possession-core::Every exit path releases the possession`. Both direct release and `release_for_party_change` leave membership unchanged. An auto-leave or terminal escort operation may then remove its own source as already specified. A manual dismissal of a possessed companion remains refused by the existing handback-first gate.

Tests must observe `release_for_party_change` before caller-owned removal, and separately confirm that an actual removal can still complete without stashing the NPC. Do not assert continuing combat/possession eligibility after legitimate membership removal. Likewise, an intentionally remote companion retains its own pre-release room; co-location and repeat-possession scenarios apply when the two bodies share a room. This preserves the approved possessed-movement model and avoids teleporting either figure.

### 4. Disconnect is explicitly deferred after checking lifecycle ordering

Installed Evennia 6.1 sources establish two distinct paths.

- `evennia/server/serversession.py::ServerSession.at_disconnect` lines 160-171 calls `account.unpuppet_object(self)` before `account.at_post_disconnect()`. The inherited stash can therefore happen before `typeclasses/accounts.py::Account.at_post_disconnect` delegates to `release_on_disconnect`. By then a writer-local location snapshot can already be null.
- `evennia/server/service.py::EvenniaServer.server_maintenance` lines 115-124 independently runs `at_pre_unpuppet` and `at_post_unpuppet(None, reason=" (connection lost)")` on tagged puppets without an account. This maintenance branch contains no account disconnect-hook call. It has no guaranteed before/after relationship to that hook and can run after a crash without it.

Consequently this change does not claim disconnect room preservation, does not change the `reason="disconnect"` branch, and does not weaken the existing disconnect binding/lock cleanup contract or multisession guard. The supplied inconclusive direct probe never passed that guard and is not coverage evidence. The named follow-up `fix-disconnected-possession-room-lifecycle` must own room survival at the earlier session-unpuppet and independent maintenance boundaries, cover final-session versus still-driven sessions with real lifecycle tests, and decide how a disconnected owner's D4 body resumes ordinary logout behavior. That work is deliberately separate from this one-day normal-release fix; no second proposal is created here.

### 5. Reuse the release boundary event

`docs/superpowers/specs/2026-09-02-observability-logging-design.md` §4.2 requires an info event at persistent state boundaries. Keep one `world.observability.log_info("possession_release", ...)` per successful release. Existing `char`, `npc`, and `reason` identify the transition; add `room` with the companion's final room id so the corrected spatial state is attributable. Add a concise `possession_release` row with those keys to the §4.2 catalog. A second restoration event would duplicate the same release boundary and is unnecessary. The existing event name and core single-event contract remain unchanged.

Tests patch `world.rules.possession.log_info`, assert the successful reason and room context for both normal release reasons, and assert no successful-release event after refusal or an idempotent second release. Run observability lint with the focused tests because this changes a logging path.

### 6. Extend the registered integration module and trace the new requirement

Use `world/rules/tests/test_possession_transition.py::PossessionTransitionTests` and `PossessionTransitionCommandTests`, both already based on `EvenniaTest`. Its module is already listed exactly once in `.github/evennia-shards.json`. Keep new behavior tests there, with synthetic companions and real account/session hooks. Do not mock `_unpuppet`, `unpuppet_object`, or the default character stash out of the regression; the room assertion must fail on the unmodified implementation. External optional narrative services can remain isolated by existing fixtures.

Exercise the actual 歸位 command from the companion caller and `release_for_party_change` independently. Check persisted `db_location_id`, live `location`, room contents, membership, logout Attribute absence, bindings, and puppet/lock/cmdset state. With membership retained and other gates passing, re-enter possession of the same NPC, release it, move the owner to a synthetic second room, invoke real `follow_companions`, and assert `combat_companions` includes the same NPC. This uses the eligibility boundary and needs no combat simulation or random result.

Extend existing refusal/write-failure tests with location and Attribute assertions, including an injected failure after residual cleanup and an outer party-control compensation case. Pin that the owner remains physically present and entranced during possession, the entry/handback epoch sequence remains unchanged, and the released companion is present when handback synchronization runs.

Annotate substantive methods with `covers_requirement` using the canonical ID obtained from `tools.spec_traceability list` over an equivalent main-spec tree with this ADDED delta merged, as documented in `docs/development/spec-test-traceability.md`. Do not guess the ID or treat a pre-sync `check` pass as proof that the future requirement is covered. Active-change deltas are outside the current-contract index. Keep current-tree checks passing during apply, then require the annotation and merged-spec check at the sync/archive boundary in the same implementation lifecycle.

No new module or shard edit is expected. If apply introduces or moves a module despite this choice, register it in exactly one shard and run `tests.test_evennia_test_optimization_contract` in the same change. Command docs and `tests/test_command_docs.py` remain intentionally unchanged because the command surface is unchanged; if that surface changes during apply, both `docs/game/commands.md` and `docs/game/command-reference.md` plus the command-doc contract must accompany it.

## Risks / Trade-offs

- [Framework hook and database caches differ] -> Snapshot location and Attribute presence/value, compensate after the failed atomic, and assert both live surfaces and persisted rows. Restoring database rows alone is insufficient.
- [Temporary disappearance can leak into handback snapshots] -> Restore before owner re-puppet and `synchronize_session`, with an ordering assertion. This design retains Evennia's own lifecycle prose; eliminating its transient logout announcement would require a separate hook policy.
- [Disconnect still permits an off-grid companion] -> Explicit scope exclusion and named lifecycle follow-up above. Existing disconnect tests establish control cleanup, not spatial safety.
- [Conflicting membership or movement expectations] -> Preserve core removal policy and each body's actual room; test co-location under a shared-room precondition.

## Migration Plan

Deploy the rules fix and regression tests together. No data/schema migration or startup repair runs. Objects already stranded need the existing operator repair facilities; the supplied live database evidence is not authorization to mutate them. Reverting the implementation restores old behavior without transforming saved data. This proposal commits planning artifacts only.
