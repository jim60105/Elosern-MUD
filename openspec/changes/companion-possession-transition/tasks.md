# Tasks: companion-possession-transition

## 1. Reuse the landed helpers

- [ ] 1.1 Wire `retire_sequence` (dispatcher) + `reset_client_sequence` (ingress; the verified
  epoch owner — coordinator reset + ndb actor clear) + `send_unpuppet_transition` (ingress;
  browser signal only) into the enter/release ordering — pinned by design D-T1; verify their
  signatures still match at implementation time.

## 2. The transfer

- [ ] 2.1 `world/rules/possession.py::_transfer_puppet`: retire/epoch-bump → additive
  `puppet:id(<account>)` grant → puppet B on the acting session → verify
  `get_puppet(session) is npc` → ladder (re-puppet A, strip grant, clear mirrors, fixed line) →
  release A through the OOC 離開角色 unpuppet path.
- [ ] 2.2 `_mount_cmdset` / `_unmount_cmdset`: derived character act cmdset with the denylist
  (switcher family + PlayerCharacter-only panel commands); NPC default rebuild on release.
- [ ] 2.3 `typeclasses/npcs.py::LLMNPC.at_pre_puppet`: accept the possession account (permit-only
  override, no re-verification).
- [ ] 2.4 `_release` in `release_possession`: unpuppet B → strip grant → re-puppet A with the
  ladder; mid-failure keeps state, logs `step="possession_release"`, fixed return line.

## 3. Hooks and rendering

- [ ] 3.1 `typeclasses/accounts.py::Account.at_post_disconnect`: call
  `possession.release_on_disconnect(self)`; `PlayerCharacter.at_post_unpuppet` gains NO
  possession branch (it fires on every deliberate swap — design D-T4, verified against Evennia
  6.1 sources); no shutdown-state inspection anywhere in possession code.
- [ ] 3.2 A's room-content display hook: 呆立入神 line when `db.possession` non-null.
- [ ] 3.3 Reload-survival: no code (attributes persist); pinned by test 4.4.

## 4. Tests

- [ ] 4.1 Swap mechanics (EvenniaTest, real sessions): verified swap leaves B puppeted / A
  released / grant present; injected silent-refusal leaves the prior state byte-identical;
  retire-and-epoch-reset-before-swap ordering observed (a completion Deferred started for A
  cannot publish after the swap).
- [ ] 4.2 Cmdset: 歸位 reachable while possessing; switcher family absent; denylist pinned against
  the landed `CharacterCmdSet`; default restored on release.
- [ ] 4.3 Release ladder: clean return; refused-return keeps state + facade error event + fixed
  line; idempotent retry completes.
- [ ] 4.4 `Account.at_post_disconnect` releases everything (simulate the disconnect lifecycle);
  a possession-internal `unpuppet_object` of A or B triggers NO release (mirrors survive the
  swap); reload round-trip (save/re-read) keeps mirrors + grant; `at_post_unpuppet` nomination
  still fires exactly once per swap.
- [ ] 4.5 Entranced rendering row (mirror set vs null).
- [ ] 4.6 `covers_requirement` annotations; new/renamed test modules registered in
  `.github/evennia-shards.json`.

## 5. Verification

- [ ] 5.1 Focused: `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings
  test_settings.py --keepdb world typeclasses web.webclient`.
- [ ] 5.2 `tools.spec_traceability check`; `tools.observability_lint check`;
  `compileall -q world typeclasses commands`.
