# Tasks

Read completed B's always-Deferred coordinator API first. This is one engineer-day, separated from M movement identity and S terminal/skip hooks. Write deterministic behavior tests with each owned implementation, then run focused checks once after all edits. No implementation is authorized during proposal creation.

## 1. Causal callback capture

- [ ] 1.1 Add presentation_events.py synchronous PublicationGroup/current/publication_group/on_publication_commit APIs and new test_publication_settlements.py. Prove nested reuse, rollback silence, callback rebinding and finally reset before a pending Deferred. Update group lifetime documentation with this exact behavior.
- [ ] 1.2 Migrate every presentation callback registration in the design inventory, preserving actor/epoch/authorization and actual asynchronous generation separation. Tests use two watchers and both ordinary-push/fact callback orders, including an out-of-ingress committed completion; each watcher observes zero preceding delta and one final promoted snapshot.

## 2. Queue and independent ingress integration

- [ ] 2.1 Add per-group candidate/reason promotion to B queue and propagate group_id through push/art/options/title/ingress. All public entries retain ALWAYS-Deferred actual outcome, with success, retirement, preflight/send failure and64-entry/waiter overflow assertions. Remove completed group metadata and keep no history; document exact caller outcomes.
- [ ] 2.2 Preserve independent text/graphical Deferred execution without a session-wide pending token. Capture synchronous adapter group, strip private publication_group_id from wire, attach completion/result/context before drain and preserve separate ui_sync queue barrier. Test two text Deferreds finishing in reverse order, text during graphical pending work, explicit sync between completions and retirement with queued callbacks. Register new test module once and retain existing text callback/Failure and no-retry assertions.

## 3. Focused integrated verification

- [ ] 3.1 Run P-PY below plus contract_gate after edits. M/S will enroll their domain checkpoint owners later; this slice must already exercise real ordinary grouped push behavior, with synthetic checkpoint fact injection through the production observer API, not a fake publisher.

## Verification commands

Run from repository root with untracked `.env.test` containing `MUD_TEST_SETTINGS=1` created only at apply time. New module test_publication_settlements.py belongs to exactly one .github/evennia-shards.json owner. Existing dispatcher/coordinator_push/art_push modules are regression labels. No full managed browser/evidence suite and no performance measurement.

### P-PY

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_publication_settlements web.webclient.presentation.tests.test_coordinator_push web.webclient.presentation.tests.test_art_push web.webclient.actions.tests.test_dispatcher
```

### Repository contract gate

```text
uv run --locked python -m tools.contract_gate
```

These are planned apply checks, not claimed runtime results from proposal creation.
