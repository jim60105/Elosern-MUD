## 1. Registry extensions for preset previews

- [x] 1.1 Add `description: str` to the frozen `RaceProfile` dataclass in `world/lore/races.py` (after
      the existing fields) and populate a one-line Traditional Chinese description for all three
      registry entries (`human`, `beastfolk`, `elf`).
- [x] 1.2 Add `emphasis: str` and `background: str` to the frozen `PlayerPreset` dataclass in
      `world/lore/player_presets.py` and populate all three presets (`human_wanderer`,
      `foxkin_scout`, `elf_guardian`) with allocation-emphasis and one-line background text.

## 2. Connection screen

- [x] 2.1 Rewrite the `CONNECTION_SCREEN` string in `server/conf/connection_screens.py`: a title
      banner (伊洛瑟恩大陸), a one-line premise, CONNECT / CREATE prompts, and the retained note that
      new accounts must create an adult character before entering the world. Keep it a static string
      (design.md D1); do not introduce a dynamic `connection_screen()` function.
- [x] 2.2 Add tests for the connection screen: (a) assert `settings.CONNECTION_SCREEN_MODULE`
      resolves to a module whose exported screen contains the banner, the premise line, and the
      CONNECT / CREATE prompts — this proves the configured channel actually serves the custom screen
      (the substantive test for the modified `evennia-project-skeleton` "Player can connect"
      scenario); (b) keep a direct static-content assertion of the module's string as a supplement.

## 3. World introduction for pending characters

- [x] 3.1 Create `world/intro.py` with a single `WORLD_INTRODUCTION` constant (2–3 lines of Traditional
      Chinese prose introducing 伊洛瑟恩大陸 and the journey ahead), imported by no one yet.
- [x] 3.2 Add `at_post_login(session)` to `typeclasses/accounts.py`: call `super()` first, then, only
      when the account's auto-created character is still `creation_pending`, send `WORLD_INTRODUCTION`
      and immediately render the `character` start screen (design.md D2/D6). Keep the hook side-effect
      free for activated accounts. This is the single login coordinator; the `onboarding-guide` change
      extends this same hook afterwards.
- [x] 3.3 Add integration tests (`EvenniaTest`) covering: a pending account sees the introduction
      followed by the creation start screen at login; an activated account sees neither.

## 4. `character` command restyle

- [x] 4.1 Extract the no-argument `character` presentation into a reusable renderer (design.md D6):
      a world-view framing line, then for each preset in `PLAYER_PRESET_REGISTRY` the race one-liner
      (from `RACE_REGISTRY[preset.race].description`), the emphasis one-liner, and the background
      one-liner. Render preset count and names from the registry only (design.md D4). Reuse the same
      renderer from `CmdCharacter.func` and from `Account.at_post_login`.
- [x] 4.2 Add explanatory lines to the custom-mode prompts: the race prompt explains each offered race
      via `RACE_REGISTRY[race].description`, and each allocation prompt states what that axis affects.
- [x] 4.3 Confirm `world/rules/character_creation.py` is untouched and `CmdCharacter` still calls the
      same activation APIs; no validation, gate, or atomicity change.
- [x] 4.4 Add/extend tests in `commands/tests/test_character_creation.py`: preset output lists exactly
      the registry presets with race/emphasis/background lines; custom prompts carry explanations; the
      adult gate and activation semantics still hold under the restyled output (regression, e.g.
      `age=17` still rejected).

## 5. Verification

- [x] 5.1 Run the focused suites (`commands/tests/test_character_creation.py`, the new connection
      screen test, `typeclasses/tests/`, the intro-login tests) and the full Evennia suite
      (`uv run --locked evennia test --settings settings.py .`).
- [x] 5.2 Run `uv run --locked python -m tools.spec_traceability check` after annotating the new
      requirement tests with `covers_requirement`, and keep `git diff --check` clean.
- [x] 5.3 Run `openspec validate login-creation-ux --strict` and confirm it passes.
