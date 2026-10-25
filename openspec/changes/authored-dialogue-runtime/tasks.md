# Tasks

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Mechanical registry cutover

- [x] 1.1 Migrate all 25 Python tables directly to scanner-discovered profile-key YAML using canonical bindings and unchanged dialogue-key topic IDs. The conversion is one scripted, reviewed transformation over the frozen literal tables rather than 25 hand-written files, which is what keeps this unit inside its 120-minute bound; migrate every importer/fixture and delete obsolete domain modules/classes/re-exports, then implement source-neutral ResolvedDialogueSource. Test complete inventory, profile/service distinction, greeting/unknown behavior and generated-capable provider interfaces; document temporary prose ownership/no manual registration.

## 2. Selection and transactional session delivery

Remaining units implement Shared contract v2, including host_key/source identity in context/session and static <=96/generated <=2048 IDs in all Python/UMD/Vue action, panel, receipt, completion and predecessor validators. Add worst valid ID and aggregate UTF-8 budget tests; generated-packages supplies the production provider later.

- [x] 2.1 Implement resolve_dialogue_context for the ordinary player and select_authored_topic/session forms with request dedup and rollback compensation. Add world/rules/tests/test_authored_dialogue_runtime.py covering stale envelope, duplicate after intervening topic, session-write failure, no time advancement and snapshot replay.

## 3. Transport and protocol cutover

- [ ] 3.1 Migrate CmdTalk, authored adapter, Python presenter, UMD misc.js::validateDialoguePanel/constants.js and production reducer to v3. Implement descriptor validation and handle_ui_action pre-validator request-ID injection. Test two deliberate picks versus a transport retry, populated v3 adoption and v2 rejection. Reuse catalog keys and expose all <=16 rows, with complete attributed text before scene-player integration.

## 4. Native seams and documentation

- [ ] 4.1 Keep freeform settled observer and world/quests/story_dialogue.py call paths native, test phase invalidation and guild listing/turn-in; update docs/game/commands.md and command-reference.md, replace full conflicting main-spec requirements in this change delta, and register new tests in manifests. Verify focused runtime/session/command/protocol tests and contract_gate.

## 5. Dialogue publication budgets

- [ ] 5.1 Implement the shared canonical UTF-8 Scene/bundle/panel limits and conditional 98304-byte dialogue envelope rule in Python protocol/coordinator and UMD constants/core/store before effects/session publication. Verify maximal multilingual chain/reconnect adoption, oversized pre-effect rejection and unchanged 65536-byte unrelated-envelope bounds in real protocol-store parity tests; update OOB docs in this unit.

