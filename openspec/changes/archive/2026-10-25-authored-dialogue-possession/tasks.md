# Tasks

Read design.md and the named dependency shared contracts first. All boxes are future implementation tasks; this proposal implements nothing. Each unit includes its own tests/documentation and is bounded to 45-120 minutes.

## 1. Context ownership and single-writer routing

Shared contract v2 is source-neutral. Test non-profile package-role contexts opening informational scenes with owner reading, while existing commission/service/freeform authority still refuses unsupported mutation.

- [x] 1.1 Extend resolver with complete party_scope authorization, owner relationship routing and actor session ownership; add world/rules/tests/test_authored_dialogue_possession.py for asymmetric races, dual relation records and malformed mirrors. Document actor/owner/host boundaries in resolver.

## 2. Enable every authored entry surface

- [x] 2.1 Remove authored possession rejections from adapters, command and exploration/affordance producers while retaining freeform and other restrictions. Test open/select/leave and stale capabilities through web plus text; update docs/game/commands.md and command-reference.md for availability.

## 3. Control cleanup and trade regression

- [x] 3.1 Clear actor delivery on successful release/control change through open/clear helpers, with cache rollback discipline. Add integration tests for actor portrait, owner progress identity and commander-purse/member-bag trade unchanged; update the historical possession capability delta only where authored initiation was prohibited.

## 4. Focused acceptance ownership

- [x] 4.1 Add possessed multi-line browser method to test_browser_exploration_dialogue.py and register browser/Python modules in ownership manifests; run focused tests and contract_gate. No freeform enablement or remote guild authority expansion.
  - `test_possessed_companion_plays_an_authored_scene_with_its_own_portrait` is
    written in `web/tests/browser/test_browser_exploration_dialogue.py` (real
    possession through the party window, actor portrait, two played lines) and
    registered in `.github/browser-shards.json`; the new Python module
    `world.rules.tests.test_authored_dialogue_possession` is registered in
    `.github/evennia-shards.json`. The focused Python suites and
    `contract_gate` pass locally. The managed browser suite is CI-owned
    (AGENTS.md), and the local harness failed at login for every browser test
    including pre-existing methods, so the method's execution is owed to CI
    rather than to this archive.

