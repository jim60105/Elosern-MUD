# Tasks

All tasks are implementation work for a later apply assignment. Acceptance follows the three delta specs and design D1-D4. Total budget is eight engineer-hours; each group includes its own tests/documentation, and the final group only verifies integration.

## 1. Exact protocol and authoritative descriptor references (3h)

- [x] 1.1 Cut over Python exploration and JS `PANEL_SCHEMAS.exploration` to version 4, accept unchanged null or 1..32-character ASCII-decimal refs in both entity/target validators, update all authored available payloads/shared fixtures and obsolete null-only comments; verify focused Python `test_schema.py` and Node `protocol_exploration_a/b.test.js` cases accept valid bounds and reject schema 3, malformed refs, extra fields and over-limit encoded payloads.
- [x] 1.2 Build capped art-view membership once and reuse canonical `resolve_entity` results by identity across both descriptor paths, emitting refs only for member identities with their own runtime/official URL; verify production presenter/catalog synthetic tests in existing `test_presenter.py` cover official and runtime success, both-list equality, image-bearing non-interact character, excluded/cap-dropped controls, imageless/age-ineligible/silhouette cases and possession without canonical/queue/gallery writes.
- [x] 1.3 Document the schema-4 reference contract and unchanged art membership in the existing frontend architecture/developer documentation and validator/presenter module docs; verify descriptions match accepted refs and deployment requires the producer/bundle cutover together, with no compatibility adapter or migration.

## 2. Current portrait completion refresh (1.5h)

- [x] 2.1 Extend `art_push.py` so a current matching portrait-catalog subject in exploration includes the freshly rendered available exploration panel with qualifying art/gallery/roster panels in the same `panel_update`; verify `web/webclient/tests/test_art_push.py` detects null-to-real refs in one revision, scene-only exclusion, unavailable exploration isolation and old-room/departed-subject no-push behavior, preserving the existing facade logging.
- [x] 2.2 Document the bounded companion-panel addition beside the completion publisher and frontend art-refresh contract; verify focused completion tests exercise actual notification and accepted update content without a new subscriber, full snapshot broadcast or focus action.

## 3. Consumer image and truthful fallback proof (1.5h)

- [x] 3.1 Extend Node `exploration_menu.test.js` with wire-valid decimal refs for target/entity precedence and no party/key synthesis; extend Vitest `app_client_presence_rail.test.js` and `tests/world/presence_rail.test.js` using accepted snapshots/updates for target and bystander face crops, non-party standee image, null/unknown/unavailable and failed media, changed-URL recovery and late art refresh while open; verify unchanged action payloads/router depth and no focus dispatch.
- [x] 3.2 Keep `PresenceRail`, `use-person-focus`, `StageActor` and `ReferenceArtwork` as existing consumers, making only changes required by the new regressions; update PresenceRail/AppShell stories and fixture comments to show valid references without claiming a synthetic story proves the live producer; verify the stories distinguish real images, truthful fallback and refreshing art and preserve existing component-manifest entries.

## 4. Integrated acceptance and handoff (2h)

- [ ] 4.1 Extend the existing synthetic browser exploration navigation fixture/journey with admitted server-origin image media, inspect the actual production exploration/catalog packet and assert `img.complete` plus nonzero `naturalWidth` for target/bystander medallions and non-party focus; register every new method in `.github/browser-shards.json` in the same change and any new Python module in `.github/evennia-shards.json`, and verify one focused managed browser method after a normal dist build.
- [ ] 4.2 Use agent-browser in the live client and existing Storybook at 1451×790 and 1920×1080 to record packet-to-loaded-image/face-crop/non-party-focus evidence, failed/null paths through synthetic harness tests, and unchanged controls/geometry; verify evidence distinguishes observed live results from fixture assertions, contains no credentials/shipped-content regression expectations and changes no permanent game content.
- [ ] 4.3 Run focused Python presenter/schema/art-push labels with the documented uv Evennia test environment, affected Node files and Vitest files, relevant showcase coverage, `openspec validate restore-exploration-portrait-refs --strict` and `uv run --locked python -m tools.contract_gate`; obtain traceability IDs with the CLI when syncing requirements and report exercised commands/results without running the full managed browser suite or CI-only evidence verification.
