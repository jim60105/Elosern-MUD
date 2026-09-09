## 1. Service seams

- [x] 1.1 Replace `world/art/service.py::_ensure_character_portrait`'s `queue_ensure` call with a `request_gallery_image` call carrying the subject's standard deterministic description (the authored appearance block included), no free text, no binding, and the shared default face rectangle — do NOT depend on the `fields` keyword, which `gallery-prompt-composition` introduces afterwards
- [x] 1.2 Add the gallery idempotency guard: request only when the subject's gallery holds no card and no gallery job for that subject is pending or in progress
- [x] 1.3 Keep the canonical-age check at schedule time and again immediately before the queue write, and keep the `transaction.on_commit` registration and failure isolation exactly as they are
- [x] 1.4 Route `retry_character_portrait` and `requeue_character_portrait` through the gallery request, removing every classic-record write for a character subject
- [x] 1.5 Restrict `_recover_named_portraits` to subjects with an empty gallery and no in-flight job
- [x] 1.6 Leave `_sync_registry_subjects` (scenes and monster tiers) on the classic pipeline, untouched

## 2. Creation skip flag

- [x] 2.1 Add an explicit skip flag to `world/rules/character_creation.py::finalize_player_portrait`, defaulting to generating
- [x] 2.2 Establish the named `portrait_policy` on both paths, inside the activation transaction, so a rollback leaves no portrait state either way
- [x] 2.3 Enqueue nothing on the skipped path
- [x] 2.4 Verify the `world/rules/starting_companions.py`, `world/imports/loader.py`, and `world/quests/scene_builder.py` call sites keep their current shape and post-commit ordering

## 3. Staff command

- [x] 3.1 Branch `commands/art.py::CmdArtRequeue` so a character subject key issues a gallery generation request instead of resetting a classic record, and creates no classic record
- [x] 3.2 Keep the monster branch on the classic path and let the one-card cap apply when a monster gallery card exists
- [x] 3.3 Confirm `@art retry` no longer surfaces character subjects (they own no classic records) and reports truthfully
- [x] 3.4 Keep every access check unchanged: no player-reachable art control is added

## 4. Tests

- [x] 4.1 `world/art/tests/test_service.py`: a committed creation drains to exactly one unbound default card carrying the shared rectangle, and no classic asset record exists for the subject
- [x] 4.2 The age gate rejects before any record, prompt, or card on every automatic path
- [x] 4.3 A rolled-back creation, import, and materialization produce no job and no card
- [x] 4.4 A failing gallery request or job still reports the gameplay operation as successful, with a bounded diagnostic
- [x] 4.5 Idempotency: consecutive recoveries append nothing; a seed-synced subject is not auto-generated; an in-flight job suppresses a second request
- [x] 4.6 `world/rules/tests/`: the skip flag leaves an empty gallery with the policy established and resolves to a fallback image; the default path schedules exactly one generation; a rolled-back skipped activation leaves nothing
- [x] 4.7 `world/quests/tests/` or the existing spawn suite: a materialized named occupant's gallery holds exactly one unbound card, and two quests sharing a stable key yield one card
- [x] 4.8 `commands/tests/`: `@art requeue` on a character key requests a gallery generation, creates no classic record, and leaves existing cards untouched until the new card is appended
- [x] 4.9 Confirm the scene and monster tier pipelines are unchanged by re-running their existing suites
- [x] 4.10 Annotate new tests with `covers_requirement` from `uv run --locked python -m tools.spec_traceability list`

## 5. Verification

- [x] 5.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.art world.rules world.quests world.imports commands`
- [x] 5.2 `uv run --locked python -m tools.observability_lint check`
- [x] 5.3 `uv run --locked python -m tools.spec_traceability check`
- [x] 5.4 `openspec validate gallery-autogen-retrofit --strict`
