## 1. Rendering layer

- [x] 1.1 Create `world/quests/describe.py` (pure, read-only) with
      `describe_objective(objective) -> str` covering DEFEAT, REACH, ESCORT, and
      ACQUIRE in Traditional Chinese, raising on an unknown `ObjectiveKind`.
- [x] 1.2 Add `describe_destination(locator) -> str` for ANCHOR (anchor display
      name), GRID (exact coordinates), and BOUND_INSTANCE (generic "指定的地點"
      line), resolving names from the immutable registries.
- [x] 1.3 Add `describe_quest_detail(record, definition, offer, current_tick)
      -> str` (current tick injected, never read internally) assembling display
      name, state, stage index, objective description, progress
      (`stage_progress / quantity`), the deadline line (remaining seconds =
      `deadline_tick - current_tick`, floored to whole hours while positive,
      "已逾期" when non-positive, omitted when `deadline_tick` is None), and the
      reward section (omitted when offer is None).
- [x] 1.4 Write pure unit tests in `world/quests/tests/test_describe.py` with
      `unittest.TestCase` using fixed ticks: one test per objective kind and
      destination kind, the unknown-kind raise, and deadline display pairs
      (remaining hours, expired, no-deadline) plus a reward/no-reward pair.

## 2. Command layer

- [x] 2.1 Add `CmdGuildShow` to `commands/guild.py` (`guild show`, aliases
      `guild 詳情`, `guild detail`, `任務詳情`) that resolves the record via
      `read_records`, the definition via `definition_for`, reads the branch via
      `parse_guild_registration` (unregistered → reward omitted; malformed →
      Traditional Chinese error), looks up the offer via `get_guild_offer`
      (catching only `GuildOfferNotFound` → reward omitted), and renders through
      `describe_quest_detail` with `get_world_clock().tick`.
- [x] 2.2 Handle exactly `QuestNotFound`, `QuestDataError`, and `GuildDataError`
      with Traditional Chinese messages; do not use a broad `except Exception`
      (unlike the existing `CmdGuildLog`).
- [x] 2.3 Register `CmdGuildShow` in `commands/default_cmdsets.py` on
      `CharacterCmdSet`.
- [x] 2.4 Update `CmdGuildList` to append the first-objective one-line summary
      (rendered by `describe_objective`) to each board row.
- [x] 2.5 Update `CmdGuildLog` to append a hint pointing at
      `guild show <quest_id>`.

## 3. Spec traceability and verification

- [x] 3.1 Add command/integration tests covering every delta scenario: accepted
      detail with staff absent, unknown id, no offer → reward omitted,
      unregistered → reward omitted, malformed registration → error, expired
      deadline; and board one-liner / log hint / unchanged eligibility.
- [x] 3.2 Annotate command/integration tests with
      `tools.spec_traceability.covers_requirement` for every requirement in
      `quest-detail-view` and the modified/added `guild-quest-board`
      requirements, using canonical IDs from
      `python -m tools.spec_traceability list`.
- [x] 3.3 Run `uv run --locked python -m tools.spec_traceability check`, the
      focused quest/command tests, and the full Evennia suite
      (`uv run --locked evennia test --settings settings.py .`), then run
      `openspec validate guild-quest-detail-view --strict`.
