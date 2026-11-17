# Design

## Context

See `proposal.md`. `creation_wizard.clear_draft` currently removes only `creation_draft`; the reset adapter calls it without a transaction. Activation removes that same attribute inside `activate_player_character`’s transaction and snapshots in-process caches. `gallery.remove_card` unlinks immediately after its gallery lock, so calling it unchanged inside a rollback-capable cleanup would lose files. Queue settlement already reloads its record/token under `queue_lock`.

## Goals / Non-Goals

**Goals:** rules-owned reset/preset cleanup, custom activation continuity, rollback-safe files and no late resurrection.

**Non-Goals:** identity-based invalidation, mismatch warnings, new subject keys, activated gallery behavior, image migration or a new scheduler.

## Decisions

### Explicit reset owner, separate from activation draft clearing

Add `reset_creation_draft(account, character)` to `world/rules/creation_wizard.py` and call it from `_creation_reset_adapter`. Recheck owned pending state in its transaction. It clears `creation_draft` and calls `creation_portrait.clear_draft_portrait(character)` for only the receipt-owned current/retained ids. Do not attach portrait cleanup unconditionally to `clear_draft`: activation also removes a draft and custom activation must keep its art.

The rules owner clears the character receipt; service-owned queue/gallery APIs remove only the authorized creation job/card state. Receipt validation establishes the actor’s subject and image ids; an input cannot name another subject, card or official preference. Empty/missing receipt is idempotent. Clear a recorded draft failure when clearing its receipt so the next panel is empty. Leave unrelated cards, subjects and external official files unchanged. Retain the named policy after reset; pending automatic recovery is already excluded by request slice, and no reset generation is scheduled.

### Rollback and lock order

Add a service-owned batch removal helper in `world/art/service.py` and supporting queue/gallery primitives. Under `queue_lock` then `gallery_lock`, cancel/delete matching job records and remove matching card/default/error data inside the caller’s rules transaction. The rules owner wraps that transaction in the established attribute/trait cache snapshot/restore pattern, including `creation_portrait`, `portrait_policy` and gallery/job attribute caches touched by removal.

Collect only removed cards’ confined stored identities. Register their unlinks with `on_publication_commit` so a rolled-back operation deletes no files. Release gallery lock before file publication gates; keep the existing queue-before-gallery ordering and never reacquire a held non-reentrant queue lock. A file unlink failure uses the existing bounded diagnostic/orphan-prune mechanism; it cannot restore a removed card or falsify the database commit. No startup-wide prune is called as a mid-game cleanup.

Canceled jobs are no longer present when late `settle_gallery_generated`/`settle_gallery_failed` reloads by job key. Reuse that existing token/record gate, which discards temporary output and publishes nothing. Test both orders: settle-before-reset is removed by reset, reset-before-settle is rejected by settlement. Failed database cleanup rolls back and reports failure; it must not claim reset succeeded.

### Activation disposition

In `character_creation.activate_player_character`, after deterministic preflight but before preset finalization, conditionally clear creation-owned art only for `request.mode == "preset"` in the same outer activation transaction. This must precede the shared finalizer’s post-commit ensure registration. Files unlink only after successful commit. If activation rolls back at any later write, policy/receipt/cards/jobs/files return to their prior state.

For custom activation, preserve the subject, current card and in-flight job. Clear only the staging receipt after commit-qualified activation writes, without canceling the job or removing its stored replacement metadata. The card or in-flight job satisfies `_gallery_auto_generation_pending`; there is no duplicate generation. A job admitted while pending may finish after custom activation on the same subject. Its queued description remains the admitted snapshot; no current identity reread changes it. With no existing work, normal post-commit automatic generation and skip semantics remain.

The skip flag means “schedule no automatic request”; it never deletes a previously generated card. Amend three autogen rollback scenarios from “no portrait state remains” to “no activation-added state remains; committed draft art survives”. This matches approved §7.4/14 and does not change import or NPC-spawn rollback guarantees.

### Identity edits and confirmation

No cleanup hook is added to sex/race/subrace/apparent-age edits, custom save, concept fill, step navigation or preset browsing. Only confirmed reset and committed preset activation discard draft art. No mismatch warning is created. A failed custom save retains old draft/portrait and existing activation authorization behavior; portrait success/failure itself neither confirms nor invalidates a saved draft.

## Risks / Trade-offs

File/database atomicity is provided by commit-deferred unlink, not an attempted file rollback. The shared low-level removal API must avoid changing ordinary gallery deletion semantics; optional post-commit removal is an explicit internal capability used by this owner. Two live sessions operate on one rules-owned receipt; synchronous reactor settlement and the queue lock protect request/reset ordering.

## Acceptance and documentation

Extend `world/rules/tests/test_creation_portrait.py`, `test_character_creation/test_portrait_finalization.py`, `test_activation_rollback.py`, creation reset adapter tests and queue settlement tests. Cover ready/pending/failed/unsaved reset, repeated reset, unrelated controls, both race orders, custom activation pending/ready/no-art, preset cleanup, and fault injection after cleanup/policy/final draft clear. Assert state/file sets and enqueue counts, never wall-clock latency. Extend overlay tests for retaining the same ready descriptor across identity edits without a new action or warning.

Update synchronization/developer documentation for reset and activation disposition, plus finalizer docstrings. Blueprint policy and activation-confirmation specs stay unchanged; their mechanisms already cover this flow.

```text
uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.rules.tests.test_creation_portrait
uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.rules.tests.test_character_creation.test_portrait_finalization world.rules.tests.test_character_creation.test_activation_rollback
pnpm exec vitest run web/webclient-app/tests/overlays/creation_overlay.test.js
openspec validate creation-draft-portrait-cleanup --strict
```
