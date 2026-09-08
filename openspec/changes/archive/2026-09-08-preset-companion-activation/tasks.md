## 1. Activation orchestration

- [x] 1.1 Add the orchestration entry point to `world/rules/starting_companions.py` that, for one player and one preset, builds each declared companion, calls `seed_affinity`, then calls `party.join_party`
- [x] 1.2 Track every NPC built during the call so the failure path can delete them
- [x] 1.3 On any exception, delete every built companion, restore the affected in-process surfaces, and re-raise
- [x] 1.4 Emit `log_info("starting_companion_joined", context={...})` per companion with the owner, preset key, companion key, and seeded value

## 2. Activation hook

- [x] 2.1 Call the orchestration entry point from `activate_player_character`, inside the existing `transaction.atomic()` block
- [x] 2.2 Place the call after the player's attribute writes (identity, traits, skills, inventory, equipment) and before `finalize_player_portrait`, so the builder sees a persisted key and a location
- [x] 2.3 Confirm custom mode never enters the path
- [x] 2.4 Confirm the failure path composes with the existing `except` branch that restores key, traits, and attributes

## 3. Tests

- [x] 3.1 `world/rules/tests/test_starting_companions.py`: activating `yuna_darknight` produces a `yuka_darknight` companion at the player's location, bound both ways, at the declared affinity
- [x] 3.2 `world/rules/tests/test_starting_companions.py`: the symmetric case for `yuka_darknight`
- [x] 3.3 `world/rules/tests/test_starting_companions.py`: a preset with no declared companions leaves `player.db.party` empty and changes nothing else
- [x] 3.4 `world/rules/tests/test_starting_companions.py`: a failure injected into the build, the seed, and the join each roll the whole activation back with no persisted NPC and no party state
- [x] 3.5 `world/rules/tests/test_starting_companions.py`: the starting companion counts against the four-companion bound
- [x] 3.6 `world/rules/tests/test_starting_companions.py`: dismissing the companion leaves it in the room with its affinity intact and above `invite_threshold`, and the `invite` command binds it again
- [x] 3.7 `world/rules/tests/test_starting_companions.py`: the auto-leave recheck immediately after activation does not dismiss the companion
- [x] 3.8 `world/rules/tests/test_party.py`: an activation-bound companion behaves identically to an invited one for follow, combat, and quest assist
- [x] 3.9 `world/rules/tests/test_starting_companions.py`: the same-account case — one character activated as `yuna_darknight` (a player literally named 悠奈) and a second activated as `yuka_darknight`, whose companion is also 悠奈; assert the companion takes the `-{pk}` suffix, both entities coexist, and the party binding names the right one
- [x] 3.10 Annotate the tests with `covers_requirement` using IDs from `uv run --locked python -m tools.spec_traceability list`

## 4. Verification

- [x] 4.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_starting_companions world.rules.tests.test_party world.rules.tests.test_character_creation`
- [x] 4.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb commands.tests.test_party_commands` (the real invite-command module; `commands.tests.test_invite` does not exist) confirming the re-invite path still accepts the companion
- [x] 4.3 `uv run --locked python -m tools.spec_traceability check`
- [x] 4.4 `uv run --locked python -m tools.observability_lint check`
- [x] 4.5 `openspec validate preset-companion-activation --strict`
