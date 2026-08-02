## Why

After activation a new player is left standing in `Limbo` with no introduction, no guidance, and no
first event: the freshly created character must find their own way into the world, and the first
playable minutes are silent and disorienting.

## What Changes

- **Depends on `login-creation-ux`**: that change adds the single `Account.at_post_login`
  coordinator; this change extends it rather than adding a second hook.
- **Spec amendment** to `player-character-creation`: activation is followed by a best-effort arrival
  transition that moves the character to the South Gate of 聖潔王都 (`capital_altoria`, `(2,0)`).
  The clause "Activation SHALL not create, move, or puppet an object" is amended: activation SHALL
  not create or puppet an object, and SHALL relocate the shell to the starting location only as a
  post-commit step that never rolls activation back and never counts as a player move. The "no object
  creation / no puppeting" guarantees are unchanged.
- Add a scripted beat engine under `world/onboarding/`: immutable arrival-scene data (prose, trigger,
  continuation), the guided-corridor constant, and a pure coordinator that decides the next beat.
- Add an `OnboardingGuide` component (in `typeclasses/components.py`) and create a South Gate guard
  NPC carrying it via an idempotent startup sync.
- Add a `talk` command (`CmdsTalk`) with defined syntax (`talk <npc>` / `talk <npc> <keyword>`);
  NPCs without a dialogue component receive a no-response line.
- Play the arrival scene (the first event) at the South Gate, teach `look` (via a
  `PlayerCharacter.at_look` seam) and movement through the guard's guidance, then hand off to the
  existing first-day arc. Guidance completes at the guild exterior; deviating from the guided corridor
  marks it skipped.
- Add onboarding state on the player character (`onboarded`, beat progress, guide progress,
  first-arrival-seen) written only through `world/rules/onboarding.py`; onboarding completes
  atomically inside the first 討伐低階魔物 turn-in.
- Add a 新手引導 help entry reachable after skipping.

## Capabilities

### New Capabilities
- `onboarding-guide`: the arrival scene beats, the guard's scripted guidance, the `talk` command, the
  `OnboardingGuide` component, onboarding state (flag, beats, progress, skip, reconnect), and
  completion on first hunt turn-in

### Modified Capabilities
- `player-character-creation`: the "activation does not move the shell" requirement is amended to allow
  teleport to the starting location, with its scenarios updated

## Impact

- `typeclasses/components.py` — new `OnboardingGuide` component; `typeclasses/characters.py` gains a
  `PlayerCharacter.at_look` seam for the `look` beat
- New package `world/onboarding/` (read-only scene/dialogue/corridor data + pure coordinator)
- `world/rules/onboarding.py` — deterministic state service (sole writer of onboarding state)
- `commands/` — new `CmdsTalk`; `CharacterCmdSet` gains the command
- Startup sync — `sync_guard_npc()` idempotently creates the guard at the South Gate
- `typeclasses/accounts.py` — extends the `at_post_login` coordinator added by `login-creation-ux`
- `world/rules/guild.py` — onboarding completion inside the `turn_in_quest` transaction (settlement
  logic unchanged)
- `world/help_entries.py` — 新手引導 entry
- `player-character-creation` delta spec + its tests updated
- No LLM or image-service dependency anywhere in the flow
