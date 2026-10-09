# Design

## Context

`quest_log_presenter()` (`web/webclient/presentation/quest_log.py`) builds every row from `QUEST_DEFINITION_REGISTRY`, the stored record, and `resolve_issuance()`. Its prose fields come from `world/quests/describe.py`: `describe_objective()`, `describe_deadline()`, `describe_quest_detail()` (a newline-joined summary of every field), and `describe_reward()` (a string that begins with 獎勵：). The JS mirror (`web/static/webclient/js/elosern/protocol/panels/quest_log.js`) enforces the same exact field set. `tests/test_quest_log_parity_contract.py` and `tests/test_panel_schema_version_parity_contract.py` pin the two sides together.

`describe_objective()` renders a regional species hunt as `在<region>討伐 N 隻<species>（計數變體：<variants>）`. The same string feeds `guild show`, the `objectives` tracker, and the `services` guild quest rows, and the quest-log spec requires those surfaces to agree byte for byte.

Reward claims live in `actor.db.guild_reward_claims` and are read by `world.rules.guild.parse_reward_claims()`, which the services presenter already calls without mutation.

The visual target is the approved prototype at `docs/design/quest-drawer-redesign/`.

## Goals / Non-Goals

**Goals:**
- Ship every field the redesigned quest drawer needs as data, not prose to parse.
- Keep every text consumer (`guild show`, the tracker, the counter rows) byte-identical.

**Non-Goals:**
- No new bound on how many reward items an issuance may register (see Decision 4).
- No change to `describe_quest_detail()`; `guild show` still uses it.

## Decisions

1. **Split seams, keep composers.** Add `describe_objective_parts(objective) -> tuple[str, str | None]` and make `describe_objective()` return `line` or `f"{line}（{note}）"`. Add `describe_reward_parts(reward) -> dict` and keep `describe_reward()` unchanged. The alternative, changing `describe_objective()` itself, would break the tracker and counter parity and `guild show` text. A byte-identity test over every registered definition and offer guards the composers.
2. **`category` is a stable wire key.** Map `QuestType` members to `gather|defeat|escort|explore|emergency` by member name, lowercased. The enum's values are zh display labels; putting them on the wire would make a wording edit a protocol change. The client owns the label and glyph per key.
3. **`grade` is validated by shape, not by registry membership, on the client.** The server validator checks that the key is in `GUILD_RANK_REGISTRY`. The JS mirror checks only a non-empty key of at most `SERVICES_MAX_RANK_KEY` characters, the same rule the services rank fields use, so authored rank data is not duplicated into JS.
4. **Reward items are capped at the panel, guarded by a data-contract test.** `QUEST_LOG_MAX_REWARD_ITEMS = 1` bounds `reward.items` in both validators, and the presenter fails closed beyond it. The prescribed twelve-row maximal CJK envelope with eight items measured 99,754 bytes, exceeding 65,536 bytes. The reduced cap preserves transport headroom. A tagged data-contract test asserts that every registered guild offer and private issuance carries at most one item. Registration remains unchanged.
5. **`reward_claimed` reuses the counter's reader.** The presenter calls `parse_reward_claims()` on the same `quest_source` it already reads records from (the owner when possessed), and reports `quest_id in claims`. Counter turn-in and automatic settlement both append to this one ledger (`write_reward_claims()`), so no settlement-specific branch is needed. A `RewardClaimError` degrades the whole panel to the common unavailable form, like a corrupt quest log.
6. **Bounds reuse existing constants.** `objective_note` uses `MAX_OBJECTIVE_LINE_CODE_POINTS`. `rationale` and `flavor` use `MAX_DEFINITION_PROSE_LENGTH` (240). Item `display_name` uses `MAX_DISPLAY_NAME_CODE_POINTS`, and `item_key` uses `MAX_KEY_CODE_POINTS`. The envelope test builds twelve rows with maximal CJK prose and one maximal item each. A client snapshot test includes accompanying tracker/services panels and metadata. Code-point bounds alone do not guarantee byte size for every Unicode/JSON-escaped combination; the unchanged closing byte check rejects oversized combinations.
7. **Interim `QuestLog.vue`.** The current component renders `flavor` where `detail` was, renders `rationale` under it when present, and formats `reward` client-side. The redesign replaces this component in `quest-drawer-book-tab`. Keeping it rendering on v2 keeps `master` shippable between changes.

## Risks / Trade-offs

- [Max-size payload exceeds the envelope] → Decision 6's test runs first. If it fails, lower `QUEST_LOG_MAX_REWARD_ITEMS` and record the new value in the spec before continuing.
- [Composer drift breaks counter and tracker parity] → the byte-identity test runs over every registered definition, plus the existing parity scenarios.
- [Fixtures hide live defects again] → story and protocol fixtures use real catalog prose, the full branch label, an item reward, and a deadline. The tagged data-contract rule applies only to tests that name shipped content, not to Storybook fixtures.
