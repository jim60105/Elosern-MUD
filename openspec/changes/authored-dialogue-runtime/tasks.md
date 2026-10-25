# Tasks

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Mechanical registry cutover

- [ ] 1.1 Convert every existing dialogue table/import/test fixture to stable topic IDs and real two-line data; remove obsolete classes/re-exports. Add synthetic resolver tests for known, unknown, greeting and generated source distinctions, and document temporary prose ownership in design-linked module comments.

## 2. Selection and transactional session delivery

- [ ] 2.1 Implement resolve_dialogue_context for the ordinary player and select_authored_topic/session forms with request dedup and rollback compensation. Add world/rules/tests/test_authored_dialogue_runtime.py covering stale envelope, duplicate after intervening topic, session-write failure, no time advancement and snapshot replay.

## 3. Transport and protocol cutover

- [ ] 3.1 Migrate CmdTalk, authored adapter, Python presenter, UMD misc.js::validateDialoguePanel/constants.js and production reducer to v3. Implement descriptor validation and handle_ui_action pre-validator request-ID injection. Test two deliberate picks versus a transport retry, populated v3 adoption and v2 rejection. Reuse catalog keys and expose all <=16 rows, with complete attributed text before scene-player integration.

## 4. Native seams and documentation

- [ ] 4.1 Keep freeform settled observer and world/quests/story_dialogue.py call paths native, test phase invalidation and guild listing/turn-in; update docs/game/commands.md and command-reference.md, replace full conflicting main-spec requirements in this change delta, and register new tests in manifests. Verify focused runtime/session/command/protocol tests and contract_gate.

## 5. Dialogue publication budgets

- [ ] 5.1 Implement the shared canonical UTF-8 Scene/bundle/panel limits and conditional 98304-byte dialogue envelope rule in Python protocol/coordinator and UMD constants/core/store before effects/session publication. Verify maximal multilingual chain/reconnect adoption, oversized pre-effect rejection and unchanged 65536-byte unrelated-envelope bounds in real protocol-store parity tests; update OOB docs in this unit.

