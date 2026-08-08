# party-core Tasks

## 1. Membership module

- [x] 1.1 Create `world/rules/party.py` with `PARTY_MAX_COMPANIONS = 4`, `join_party(npc, player)`,
      `leave_party(npc, player, reason)`, and `purge_npc_memberships(npc)` as the sole writers of
      `player.db.party` (list of NPC dbids) and `npc.db.party_member` (player dbid); join validates
      NPC target, co-location, absence of an existing binding, and the 4-companion bound; all
      functions write inside one `transaction.atomic()` with snapshot/restore of both attributes
      and idempotent re-application; stale dbids (deleted NPCs) read as absent companions, never
      raise.
- [x] 1.2 Add the `NPC.at_object_delete` hook calling `purge_npc_memberships(self)` so instance
      reclamation, scene teardown, and ordinary deletes free companion slots.
- [x] 1.3 Add a membership-ownership contract test: no module outside `world/rules/party.py`
      assigns `db.party` or `db.party_member`.
- [x] 1.4 Add unit/integration tests: valid join binds both sides; party-bound rejection at 4;
      remote-NPC rejection; duplicate-join rejection; fault injection restores both entities; the
      binding survives a simulated reload; deleting a bound NPC frees the slot and shrinks the
      party; a stale dbid is treated as absent.

## 2. Structured dialogue outcome

- [x] 2.1 Add `run_npc_exchange(speech, character, client)` to `typeclasses/npcs.py` returning a
      frozen `DialogueExchangeResult(degraded: bool, reply: NPCDialogueReply | None)`: memory
      append and thinking timer as in `at_talked_to`, but no intent application.
- [x] 2.2 Refactor `at_talked_to` to compose `run_npc_exchange` + intent application with
      unchanged observable behavior; add typeclass tests proving both behaviors stay green.
- [x] 2.3 Add dialogue-intent work: extend `NPC_INTENT_KINDS` and `NPC_DIALOGUE_OUTPUT_SCHEMA` in
      `world/ai/npc_dialogue.py` to eight kinds with `party_invite` carrying a boolean `accept`.
- [x] 2.4 Add the per-kind semantic validator `_validate_party_payload` (exactly one field
      `accept`, a bool) and register it; keep registration atomic/idempotent.
- [x] 2.5 In `world/rules/npc_intents.py`, route `party_invite` with `accept: true` to
      `join_party(npc, player)` (re-verifying co-location, binding, bound) and `accept: false` to
      an applied no-op; illegal payloads or rejected joins are discarded with the speech kept, and
      the rejection reason (full party, duplicate, remote) is distinguishable in `IntentOutcome`.
- [x] 2.6 Add validator/applier tests: valid `{accept: true|false}` passes; non-boolean, missing,
      or extra payload rejected and retried; join-gate failures discard only the intent and
      surface the distinct reason.

## 3. Commands and actions

- [x] 3.1 Add `commands/invite.py`: `invite <npc> [訊息]` (aliases 邀請, 組隊) resolving a local NPC
      like `talk`, preflighting the deterministic gate (NPC, not already a companion, party not
      full), running `run_npc_exchange` with the invitation message via `build_dialogue_client()`,
      applying the fixed threshold ONLY on `degraded=True` (never overriding an AI decision),
      otherwise showing the speech and routing the intent through `apply_npc_intent`, and rendering
      join/refusal/full-party/rejected notifications.
- [x] 3.2 Add `commands/leave.py`: `leave <npc>` (alias 解散) resolving a bound companion and
      dismissing via `leave_party(..., reason="dismissed")` with no affinity change.
- [x] 3.3 Mount `invite` and `leave` on the character cmdset (`commands/default_cmdsets.py`).
- [x] 3.4 Add the webclient action pair `explore.party_invite` / `explore.party_leave` reusing the
      same deterministic APIs and the injected client, with payload validation mirroring the talk
      actions; register both actions in the action registry, extend the exploration presenter and
      the Python/JS protocol validators (adding the two action IDs to `ACTION_IDS` /
      `EXPLORATION_ACTION_IDS` and the parity fragments in
      `tests/test_exploration_parity_contract.py`), and add the webclient affordances for them
      (`explore.party_invite` for a present unbound `LLMNPC`, enabled unless the party is full;
      `explore.party_leave` for a present bound companion), plus the matching Node JS tests.
- [x] 3.5 Wire the auto-leave hook in `world/rules/affinity.py`: replace the no-op body with the
      membership check (bound companion and affinity below threshold → `leave_party(..., reason=
      "affinity_below_threshold")`) inside the affinity write's transaction; the player
      notification fires only after the outer transaction commits.
- [x] 3.6 Add command/action tests: invite joins, AI refusal never overridden by the threshold,
      illegal intent keeps speech, full-party preflight blocks before any dialogue call, offline
      threshold accept/reject lines, already-companion rejection, full-party-after-reply
      notification, leave dismissal, unbounded leave rejection, auto-leave at 70→69 vs exactly 70,
      auto-leave fault injection rolls back the affinity write, notification timing assertions.

## 4. Documentation and verification

- [x] 4.1 Update `docs/game/commands.md` and `docs/game/command-reference.md` with `invite` and
      `leave` entries (keys, aliases, syntax, context); update `tests/test_command_docs.py`
      expectations.
- [x] 4.2 Run the touched test labels (`world.rules` party/affinity/npc-intents, `world.ai`
      npc-dialogue, `typeclasses` npc/entity, `commands`, `web.webclient.actions`,
      `web.webclient.presentation`, the Node JS tests under `web/static/webclient/js/tests/`,
      `tests/test_command_docs.py`, `tests/test_exploration_parity_contract.py`,
      `tests/test_ai_transport_contract.py`).
- [x] 4.3 Run `uv run --locked python -m compileall -q world typeclasses commands server` and keep
      `git diff --check` clean; ensure `commands/` and `world/rules/` never import `world.ai`
      directly (the client enters only through the composition root).
- [x] 4.4 Annotate substantive new tests with `covers_requirement` canonical IDs; run
      `openspec validate party-core --strict` and
      `uv run --locked python -m tools.spec_traceability check`; before handoff run the required
      test entry points with the same `OPENSPEC_TEST_EVIDENCE` path and the verifier's
      `verify --evidence` mode.
