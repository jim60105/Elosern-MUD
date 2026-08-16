# AI Action Options — Trigger Service & Cache

## Why

The generative layer (`action-options-layer`) can produce a curated `OptionSet | None`, but
nothing deterministic decides *when* to ask, dedupes across windows, remembers the answer, or
delivers it to the right sessions — so the curated row would be impossible to keep to the
one-call-per-situation cost contract and would clobber itself across reconnect, dismiss, or
puppet change. This change builds the deterministic timing core: scheduled, cached,
session-scoped delivery of proposals through the existing `ui_update` contract.

## What Changes

- New `server/option_proposal_service.py` — the single production caller of
  `generate_action_options`: fire-and-forget scheduling (`schedule_action_options(actor, *,
  watchers, client=None)`, never raises, never blocks), situation fingerprinting, per-fingerprint
  LRU cache with replay semantics, an in-flight pending registry with generation identity and
  per-session subscriber entries `PendingSubscriber(session, generation_token, captured_epoch)`,
  a 30 s negative memo, `evict(session, actor)` for the dismiss flow (the action wiring arrives
  with a later change), and puppet-change cleanup of the session options state.
- **One LLM call per cache residency** (corrected from "per service lifetime"): an evicted or
  dismissed fingerprint MAY regenerate — that is what "clear this cache" means; within a
  residency, replay is cached and concurrent triggers attach subscribers instead of calling
  again.
- Fingerprint = `sha256(room_key | sorted NPC identities | sorted monster identities |
  eligible_affordance_digest | public_state_digest)`, where the eligibility digest covers the
  canonical affordance list (action_id + params, labels excluded) so schedule-gate flips, exit
  locks, and monster death invalidate cached proposals, and the public-state digest covers only
  the objective identity the player already sees (`quest_id + stage_index + objective_summary`,
  sorted across active objectives — the fields the quest view already renders) plus public
  relationship tier labels — never raw affinity numbers, hidden stages, or counters.
- Session-scoped options presentation state: `session.ndb.options_state`
  (`{owner_actor_id, fingerprint, status, generation_token, displayed}`) owned by the service,
  cleared on puppet change, and surfaced to presenters only as an immutable
  `PresentationContext.options_state` snapshot (`OptionsSnapshot`) built by one shared
  presentation-context factory — presenters never receive the raw session.
- New `web/webclient/presentation/watchers.py` — an ephemeral, ingress-maintained
  puppet → live-session registry keyed by session identity (`watchers_for(actor)` returns each
  watcher with its *current* coordinator epoch) that the room-entry hook uses (the dialogue and
  reconnect hooks supply their watchers directly).
- New `publish_panel_update(session, actor, panels, *, context, expected_epoch)` helper on the
  coordinator: it silently publishes nothing when the captured epoch no longer matches the live
  coordinator (retired transport/puppet), and renders through the `OptionsSnapshot`-carrying
  context.
- The three trigger hook call sites themselves (room entry, dialogue completion publication,
  `ui_sync`) land with the next change; this change defines the service contract they call into
  and keeps the room-entry import seam as a pinned decision for that change.

## Capabilities

### New Capabilities

- `action-options-trigger-service`: The deterministic timing core for AI action proposals —
  situation fingerprinting with anti-oracle discipline, one-call-per-residency replay with
  explicit regeneration exceptions, per-session pending/eviction semantics with generation
  retirement, the session-scoped options presentation state (puppet-change safe), the watcher
  registry seam, and the epoch-guarded coordinator push — strictly presentation-state-only
  (no canonical game writes, no dialogue kind in v1).

### Modified Capabilities

<!-- No main-spec requirement changes: the push reuses the existing ``ui_update`` panel
     replacement contract; ``PresentationContext``/coordinator/watcher changes are internal
     presentation plumbing, not protocol behavior. -->

## Impact

- **New modules:** `server/option_proposal_service.py`,
  `web/webclient/presentation/watchers.py` (ephemeral, no persistence).
- **Modified:** `web/webclient/presentation/context.py` (frozen `options_state` snapshot field,
  `None` default keeps every existing presenter/test unchanged; single context factory),
  `web/webclient/presentation/coordinator.py` (`publish_panel_update` with epoch guard),
  `server/conf/inputfuncs.py` + `web/webclient/presentation/ingress.py` (watcher registration on
  `ui_sync`/command settlement; puppet-change clears `session.ndb.options_state` next to the
  existing `coordinator.reset()`/`retire_sequence()`).
- **Consumed contracts:** `world/ai/action_options.py` (`generate_action_options`,
  `build_options_context`) from `action-options-layer`,
  `web/webclient/presentation/affordances.py` (canonical affordance tuple + canonical-JSON
  serializer, eligibility digest source) and `default_cards()` (degraded derivation) from
  `action-options-affordance-contract`, the v5 `context_actions` suggestions contract as pinned
  by the six-doc design set (`context-actions-suggestions` delta lands in the next session; the
  dependency note in `design.md` fixes the authority), and `web/webclient/actions/dispatcher.py`'s
  `_publish_completion` hook point (consumed by the next change).
- **Layer contract dependency:** the negative memo must know a transport failure apart from an
  ordinary degrade; the layer's resolve-to-`None` contract is augmented with a typed outcome
  (ready / degraded(reason)) — carried as a dependency amendment for `action-options-layer`
  (design.md D7).
- **Deferred to follow-ups:** `options.dismiss` action + the unified three-parameter adapter ABI
  (`dismiss-options-action`); the three hook call sites (`action-options-trigger-hooks`); the
  dock/choice-point surfaces (`webclient-options-surface`, `webclient-options-choicepoints`).
- **Test surface:** `server/tests/test_option_proposal_service.py`,
  `web/webclient/presentation/tests/test_watchers.py`, coordinator push tests; FakeLLM fixtures
  via the layer; no player command, panel schema, or protocol change in this change.
- No backward-compatibility or migration concerns: the project has no released users.