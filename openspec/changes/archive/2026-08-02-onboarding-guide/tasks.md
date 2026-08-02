> **Dependency note**: this change depends on `login-creation-ux`, which adds the single
> `Account.at_post_login` coordinator. This change extends that hook; it does not add a second one.

## 1. Onboarding data package (`world/onboarding/`)

- [x] 1.1 Create the `world/onboarding/` package with `__init__.py` and a module docstring stating the
      package is read-only guidance data and coordination for onboarding (design.md D1/D2), importing
      nothing from `world.rules`, `typeclasses`, or Evennia.
- [x] 1.2 Define `scenes.py`: frozen `Beat` dataclass (`beat_id`, `prose`, `trigger`, `next_beat_id`)
      and the arrival scene beats — arrival prose at 南門, the guard's opening `look` prompt
      (`trigger=COMMAND_LOOK`), and the guidance beat prompting movement north to the plaza and the
      guild. Declare `GUIDED_CORRIDOR` as a data constant `{南門, 南大道, 中央廣場, 冒險者公會外}`
      (design.md D1/D10).
- [x] 1.3 Define `guide_dialogue.py`: frozen keyword→response table for the guard (公會, 冒險, 危險,
      再見, plus a no-understanding line), keyed by `dialogue_key`.
- [x] 1.4 Define `guide.py`: pure functions taking a plain state snapshot and returning the next beat
      output / requested transition. Define the frozen `GuideProgress` schema (`state` in
      active/completed/skipped, `seen_keywords: tuple[str, ...]`) here (design.md D2). No imports
      from `world.rules`, `typeclasses`, or Evennia.
- [x] 1.5 Add pure-logic tests (`unittest.TestCase`): one test per beat and per keyword group;
      assert `guide.py` has no rules/Evennia imports (import-graph check) — the cycle guard for
      design.md D2.

## 2. Component and guard sync

- [x] 2.1 Add `OnboardingGuide(Component)` to `typeclasses/components.py` (name `onboarding_guide`,
      `dialogue_key` DBField) following the `GuildStaff`/`Merchant` marker pattern (design.md D4).
- [x] 2.2 Implement `sync_guard_npc()` in `world/rules/onboarding.py`: create exactly one
      `NPC(LivingEntity)` at the South Gate with the `OnboardingGuide` component, stable key/tag,
      authored description, and adult identity attributes (`age` and `apparent_age`, both >= 18);
      idempotent across repeated runs (design.md D4).
- [x] 2.3 Register `sync_guard_npc()` in `server/conf/at_server_startstop.py::at_server_start` after
      `sync_grid()`; missing South Gate logs a warning and skips (design.md risk row 3).
- [x] 2.4 Test: repeated `sync_guard_npc()` produces exactly one guard and the guard's actual and
      apparent ages are both >= 18 (EvenniaTest).

## 3. State service (`world/rules/onboarding.py`)

- [x] 3.1 Implement the four onboarding attributes as `AttributeProperty` on `PlayerCharacter`
      (`onboarded=False`, `onboarding_beat=None`, `guide_progress=dict`, `first_arrival_seen=False`)
      and the service functions that read/write them — every write goes through this module.
- [x] 3.2 Implement `relocate_to_starting_location(character)`: a best-effort relocation to 南門 after
      a successful activation commit; never rolls back activation, never advances the world clock,
      never emits a player-move event; missing 南門 leaves the shell in place and yields a degradation
      notice (design.md D3).
- [x] 3.3 Implement `maybe_play_arrival(character)`: play the arrival scene only for an onboarding
      character at the South Gate whose arrival beat is incomplete; invoked after relocation, from the
      extended `Account.at_post_login`, and from the room-entry observer (design.md D3/D7/D10).
- [x] 3.4 Implement `advance_beat`, `mark_guide_skipped`, and `set_onboarded`; persist
      `guide_progress` strictly through the `GuideProgress` schema (design.md D2).
- [x] 3.5 Implement `observe_room_entry(character)`: entering a room outside `GUIDED_CORRIDOR` marks
      the guide skipped; entering 冒險者公會外 completes guidance. All room-key checks live here
      (design.md D10).
- [x] 3.6 Implement `talk_response(npc, character, keyword)`: require `OnboardingGuide`, look up the
      `dialogue_key` table, return authored prose or the no-understanding line, update
      `guide_progress.seen_keywords` (design.md D5).
- [x] 3.7 Add the completion inside `world/rules/guild.py::turn_in_quest`: the onboarding write for the
      `introductory_hunt` quest runs inside the SAME transaction and rollback scope as the settlement,
      so a failure rolls back the claim together with `onboarded`; `ALREADY_CLAIMED` keeps it
      single-fire (design.md D6).

## 4. Look seam, commands, hooks, and help

- [x] 4.1 Override `PlayerCharacter.at_look` in `typeclasses/characters.py`: after a successful look,
      if the character is onboarding at the South Gate with the arrival beat active, call the rules
      service to advance the beat and append the guidance prompt to the returned text; a look
      elsewhere or a failed look never advances (design.md D9).
- [x] 4.2 Create `CmdsTalk` in `commands/` (new module) implementing `talk <npc>` and
      `talk <npc> <keyword>` with distinct lines for missing/ambiguous/non-NPC targets, component-less
      NPCs, and unknown keywords (design.md D5); add it to `CharacterCmdSet` in
      `commands/default_cmdsets.py`.
- [x] 4.3 Wire the room-entry observer: `GridRoom.at_object_receive` already runs
      `QuestObservableRoomMixin`; add the onboarding observer call after it so 南門/公會外/corridor
      entries reach `observe_room_entry` (design.md D10).
- [x] 4.4 Extend `Account.at_post_login` (added by `login-creation-ux`) to call `maybe_play_arrival`
      for an activated character at the South Gate with an incomplete arrival beat (design.md D7).
- [x] 4.5 Add the 新手引導 entry to `world/help_entries.py` (arrival, guard, first-day path).

## 5. Player-character-creation delta and activation tests

- [x] 5.1 The MODIFIED delta spec (`specs/player-character-creation/spec.md`) splits atomic activation
      from best-effort relocation; keep it in sync with the main spec during implementation.
- [x] 5.2 Update `commands/tests/test_character_creation.py`: activation asserts the shell's location
      is 南門 (dbref/membership/puppeting unchanged) and the relocation does not advance the world
      clock; a missing-South-Gate case leaves the shell in place with a degradation notice while
      activation still succeeds; a failed relocation never rolls back activation.
- [x] 5.3 Add `world/rules/tests/` onboarding-state tests: `advance_beat`, corridor skip (room outside
      `GUIDED_CORRIDOR` sets guide-skipped, `onboarded` stays false), guild-exterior completion,
      `GuideProgress` schema round-trips, `talk_response` component/keyword/progress cases.
- [x] 5.4 Add arrival/guard integration tests (`EvenniaTest`): activation → relocation → arrival scene →
      `look` advances → guard prompts north → `talk` keyword answers; look elsewhere does not advance;
      reconnect replays incomplete arrival; completed arrival never replays.
- [x] 5.5 Add turn-in atomicity tests: an injected failure in the onboarding write inside
      `turn_in_quest` rolls back the whole settlement (`onboarded` stays false, no partially applied
      reward or claim); a double turn-in does not repeat the closing line or re-set `onboarded`.

## 6. Full-journey integration and verification

- [x] 6.1 `EvenniaTest` full-journey test: create → activate → arrive → `look` → north → guild
      register → accept 討伐低階魔物 → wilderness hunt → turn in → `onboarded=True` and no further
      guidance.
- [x] 6.2 Run the full Evennia suite (`uv run --locked evennia test --settings settings.py .`),
      `uv run --locked -m unittest discover tests`, and keep `git diff --check` clean.
- [x] 6.3 Confirm no module under `world/onboarding/` imports `world.rules`, `typeclasses`, or Evennia
      (grep spot-check for the design.md D2 cycle guard).
- [x] 6.4 Annotate tests with canonical requirement IDs obtained via
      `uv run --locked python -m tools.spec_traceability list` — including the MODIFIED
      `player-character-creation` requirement ID on the new South Gate/fallback/relocation tests and
      the new `onboarding-guide` requirement IDs on their tests — then run
      `uv run --locked python -m tools.spec_traceability check`.
- [x] 6.5 Run `openspec validate onboarding-guide --strict` and confirm it passes.
