# Tasks

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Mechanical registry cutover

- [ ] 1.1 Convert every existing dialogue table/import/test fixture to stable topic IDs and real two-line data; remove obsolete classes/re-exports. Add synthetic resolver tests for known, unknown, greeting and generated source distinctions, and document temporary prose ownership in design-linked module comments.

## 2. Selection and transactional session delivery

- [ ] 2.1 Implement resolve_dialogue_context for the ordinary player and select_authored_topic/session forms with request dedup and rollback compensation. Add world/rules/tests/test_authored_dialogue_runtime.py covering stale envelope, duplicate after intervening topic, session-write failure, no time advancement and snapshot replay.

## 3. Transport and protocol cutover

- [ ] 3.1 Migrate CmdTalk and authored web adapter payload validator, Python presenter, UMD exotic.js validator and dialogue-view.js to v3. Reuse catalog keys. Add server/client mirror tests and expose all <=16 rows through existing scrollable choices, with complete attributed current-window text before scene-player integration.

## 4. Native seams and documentation

- [ ] 4.1 Keep freeform settled observer and world/quests/story_dialogue.py call paths native, test phase invalidation and guild listing/turn-in; update docs/game/commands.md and command-reference.md, replace full conflicting main-spec requirements in this change delta, and register new tests in manifests. Verify focused runtime/session/command/protocol tests and contract_gate.

