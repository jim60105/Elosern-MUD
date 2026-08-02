## Why

After accepting a guild quest, a player cannot see what the quest actually asks
them to do: `guild log` shows only the quest id, state, and stage index, and
`guild list` shows only names and rewards. A new player who accepts the
introductory hunt has no way to learn its completion condition (討伐 1 隻低階魔物)
from inside the game, which makes the deterministic first-day arc opaque.

## What Changes

- Add a player-facing `guild show <quest_id>` command (aliases `guild 詳情`,
  `guild detail`, `任務詳情`) that renders one quest record's full detail:
  display name, state, current stage, the current objective's description and
  progress, remaining deadline (when the definition sets one), and the reward
  when an offer for that definition exists at the player's registered branch.
  Like `guild log`, it reads the player's own quest log and requires no local
  guild staff presence; the `guild-quest-board` "local service host" requirement
  is explicitly amended so read-only personal quest-log commands (`guild log`,
  `guild show`) are exempt from the service-host search.
- Add a small read-only presentation layer under `world/quests/` that renders
  immutable `QuestObjective`/`RoomLocator` values into Traditional Chinese
  objective prose and assembles a quest detail from a record + definition +
  current world tick (injected, so the renderer stays pure and unit-testable);
  the command layer stays thin.
- Enhance `guild list` so each board row includes a one-line objective summary,
  letting a player know what an offer demands before accepting it.
- Enhance `guild log` output with a one-line hint pointing at `guild show` for
  full details.
- Amend the `guild-quest-board` main spec with a requirement covering player
  quest-detail viewing and board objective summaries, with traceable tests.

No backward-compatibility or migration work is needed (pre-release project).

## Capabilities

### New Capabilities

- `quest-detail-view`: read-only rendering of quest records and objectives for
  the player-facing quest-detail command.

### Modified Capabilities

- `guild-quest-board`: the player-facing guild command requirements gain a
  quest-detail viewing command, and the board-listing requirement gains the
  one-line objective summary.

## Impact

- `commands/guild.py`: new `CmdGuildShow`; small output changes to
  `CmdGuildList` and `CmdGuildLog`.
- `commands/default_cmdsets.py`: register `CmdGuildShow` on the character
  cmdset.
- New `world/quests/describe.py` (or equivalent) — read-only objective/detail
  rendering; imports only immutable registries (`world/lore`, quest
  definitions) and no writers.
- Tests: new pure-logic tests for the rendering layer
  (`world/quests/tests/test_describe.py`), command-level coverage in
  `commands/tests/test_guild_economy_commands.py`, and
  `tools.spec_traceability.covers_requirement` annotations for every new or
  amended requirement.
