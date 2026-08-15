## 1. Shared fingerprint primitives

- [ ] 1.1 Read the canonical affordance builders from `action-options-affordance-contract`; add
      the shared canonical-JSON serializer (key-sorted, deterministic type coercion) next to
      them, exported for the ladder, the fingerprint, and test fixtures
- [ ] 1.2 Implement `displayed_objective_identity(actor)` — the single read-only helper returning
      the sorted `(quest_id, stage_index, objective_summary)` tuples of the active objectives
      the quest view renders (never stage counters or thresholds)
- [ ] 1.3 Implement `fingerprint(room_key, npc_ids, monster_ids, eligible_affordance_digest,
      public_state_digest)` with the eligibility digest over sorted `(action_id, params)` pairs
      (labels excluded)
- [ ] 1.4 Pure `unittest.TestCase` suite: identical-input replay, schedule-flip/exit-lock/
      monster-death invalidation via the eligibility digest, partial-progress and sub-tier
      affinity stability (anti-oracle fixtures), multiple-objective determinism, canonical
      serialization parity with the ladder comparison

## 2. Watcher registry

- [ ] 2.1 Implement `web/webclient/presentation/watchers.py`: per-actor map keyed by session
      identity, idempotent registration, `watchers_for(actor)` reading each watcher's current
      coordinator epoch at query time, pruning disconnected/repuppeted sessions at every
      registration, never registering non-webclient or unpuppeted sessions
- [ ] 2.2 Wire registration into the `ui_sync` path and command settlement in
      `server/conf/inputfuncs.py` / `web/webclient/presentation/ingress.py`, keeping the
      refresh paths unchanged
- [ ] 2.3 `web/webclient/presentation/tests/test_watchers.py`: idempotent registration, epoch
      freshness after coordinator reset, unconnected-session pruning, non-webclient/unpuppeted
      never registered

## 3. Options snapshot and the single context factory

- [ ] 3.1 Add the frozen `OptionsSnapshot` dataclass and the `options_state: OptionsSnapshot |
      None = None` field to `PresentationContext` (default `None`; every existing constructor
      and test stays `None`)
- [ ] 3.2 Introduce the single presentation-context factory (ingress, every dispatcher
      publication path, and the service push all build contexts through it) that snapshots
      `session.ndb.options_state` immutably and refuses to surface a snapshot whose
      `owner_actor_id` differs from the puppet
- [ ] 3.3 Presenter-level tests: a `context_actions` presenter renders `suggestions` from the
      snapshot field only (no raw session access) — with the six-doc wire-shape fixtures from
      the `context-actions-v3` contract — and one state-preservation test per `ui_sync`,
      completion, internal-error, and stale-refresh path

## 4. Trigger service core

- [ ] 4.1 Implement `server/option_proposal_service.py`: fingerprint floor, per-fingerprint LRU
      (cap 16) with replay, negative memo (30 s TTL, injectable clock, transport-failure-only),
      pending registry with generation identity and per-session
      `PendingSubscriber(session, generation_token, captured_epoch)`, and the per-session
      `session.ndb.options_state` owner
- [ ] 4.2 Implement `schedule_action_options(actor, *, watchers, client=None)`: fire-and-forget
      (never raises, never blocks), offline stub client, function-local `world.ai` imports,
      errback logging; the single production caller of `generate_action_options`
- [ ] 4.3 Implement the generation flow: generating publish only on non-generating transitions;
      success → validate/cache/publish `ready`; degraded outcome → publish `degraded` as a
      fresh `default_cards()` derivation; transport failure → memo + `degraded`; delivery
      guarded per subscriber by token AND captured epoch; an emptied pending generation (last
      subscriber dismissed) is retired — its completion writes no cache, memo, or state
- [ ] 4.4 Implement `evict(session, actor)`: displayed-fingerprint targeting, global cache+memo
      removal, per-session pending removal with generation retirement on last subscriber, token
      increment, `unavailable` state + guarded `suggestions.status="unavailable"` publish
- [ ] 4.5 Add the puppet-change cleanup: the ingress puppet-change branch and
      `reset_client_sequence` clear `session.ndb.options_state` next to the existing
      coordinator reset / sequence retirement
- [ ] 4.6 `server/tests/test_option_proposal_service.py` (deferred `unittest`/EvenniaTest
      hybrids following the repo patterns): replay one-call, pending subscriber attach, LRU and
      dismiss regeneration, generating→generating silence, token/epoch staleness, last-
      subscriber retirement (in-flight completion writes nothing), multi-session dismiss
      isolation, memo TTL with injected clock, transport-vs-degrade memo discrimination,
      disabled/offline paths, vanished-room no-op, repuppet A→B state cleanup, eviction
      regeneration

## 5. Epoch-guarded push helper

- [ ] 5.1 Implement `publish_panel_update(session, actor, panels, *, context, expected_epoch)` on
      the coordinator: epoch match → exact `ui_update` envelope at a new revision; mismatch →
      silent no-op
- [ ] 5.2 Coordinator tests: successful push shape/revision, mismatch no-op, retirement
      simulation (coordinator reset between capture and push)

## 6. Verification

- [ ] 6.1 Record the `action-options-layer` outcome amendment (`OptionGenerationOutcome` with
      `reason`) as a MODIFIED delta on that change before implementing the memo
      discrimination; the service keeps the controlled-failure fallback until the amendment
      lands
- [ ] 6.2 Run the owned package tests (`server`, `web.webclient`) until green, plus
      `tests/test_command_docs.py` (no player command changes) and
      `uv run --locked python -m tools.spec_traceability check`
- [ ] 6.3 Run `openspec validate action-options-trigger-service --strict`; mark tasks complete
      only after their behavior is verified by the corresponding tests