## Why

Two guidance gaps break the new-player arc: (1) the South Gate guard's guidance
tells the player to go north through 中央廣場 to reach the guild, but the guild
exterior (冒險者公會外) actually lies east of 南大道, so the guard points the
wrong way; and (2) talking to the guild master NPC (who carries `GuildStaff`/
`GuildExaminer` components but no dialogue) yields only "對方沒有理會你", so a new
player arriving at the guild has no idea the `guild register` / `guild list` /
`guild accept` / `guild turnin` commands exist.

## What Changes

- Correct the guard's direction to the guild in all authored guidance:
  - `GUIDANCE_BEAT` prose in `world/onboarding/scenes.py` — go north to 南大道,
    then east to 冒險者公會外 (not north through the plaza).
  - The 公會 keyword response in `world/onboarding/guide_dialogue.py`.
  - The 新手引導 help entry in `world/help_entries.py`.
  - The `2026-08-02-player-onboarding-design.md` Beat 5 line is amended to
    record the map-authoritative two-step route.
- Make the guild master a scripted dialogue host:
  - Add a generic `ScriptedDialogue` component (carrying a `dialogue_key`)
    alongside the existing `OnboardingGuide` component.
  - Add a `guild_staff` dialogue definition teaching the guild commands with a
    no-keyword greeting line. **DEPENDENCY:** the taught command list includes
    `guild show`, which is provided by the separate change
    `guild-quest-detail-view`; this change SHALL be applied and verified only
    after that change exists, otherwise `guild show` is omitted from the list.
  - Generalize the `talk` command / dialogue service so any dialogue-capable NPC
    (guard or scripted host) responds; guard-specific keyword tracking on
    `guide_progress` stays exclusive to the `OnboardingGuide` host.
  - Attach `ScriptedDialogue` to the guild master host in
    `world/rules/guild_economy.py` sync (idempotent, alongside `GuildStaff`).
- Update affected tests to assert the corrected direction (including a
  map-path assertion 南門 → 南大道 → 冒險者公會外) and the new guild-staff talk
  behavior; amend the `onboarding-guide` main spec (direction) and the
  `guild-registration` spec as needed for the dialogue-host capability.

No backward-compatibility or migration work is needed (pre-release project).

## Capabilities

### New Capabilities

- `scripted-dialogue`: a generic component + immutable keyword-table mechanism
  that lets service NPCs (such as guild staff) answer authored `talk` lines and
  teach players the relevant commands.

### Modified Capabilities

- `onboarding-guide`: the guard-guidance requirement's direction is corrected to
  match the actual city map, and the `talk` requirement generalizes to any
  scripted dialogue host.
- `guild-registration`: the guild service components requirement gains the
  scripted-dialogue capability on the guild master host.

## Impact

- `world/onboarding/scenes.py` — corrected `GUIDANCE_BEAT` prose.
- `world/onboarding/guide_dialogue.py` — corrected 公會 response; new
  `guild_staff` table (reuses the existing keyed `DIALOGUE_TABLE`).
- `world/help_entries.py` — corrected 新手引導 direction prose.
- `typeclasses/components.py` — new `ScriptedDialogue` component.
- `world/rules/onboarding.py` (or a sibling rules module) — generalized
  dialogue-host resolution used by `commands/talk.py`; guard-only state writes
  preserved.
- `commands/talk.py` — respond to scripted dialogue hosts and present a
  no-keyword topic line for them.
- `world/rules/guild_economy.py` — attach `ScriptedDialogue` to the guild master
  in `sync_service_content`.
- Tests: `world/rules/tests/test_onboarding.py`,
  `world/onboarding/tests/test_onboarding_data.py`,
  `world/rules/tests/test_onboarding_journey.py`, `world/rules/tests/
  test_guild_economy_sync.py`, and `commands/tests/` — plus
  `tools.spec_traceability.covers_requirement` annotations for every amended or
  new requirement.
