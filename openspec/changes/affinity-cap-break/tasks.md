# affinity-cap-break — Tasks

## 1. Rulebook cap_breaks table

- [ ] 1.1 Add a `cap_breaks` list to `world/rules/rulebook/affinity.yaml` with one documented
      example entry (`npc_key` or `role`, `quest_key`, `new_cap`)
- [ ] 1.2 Extend `world/rules/affinity_config.py` to load and validate `cap_breaks`: non-empty
      `quest_key` that resolves in the quest definition registry, exactly one of `npc_key`/`role`,
      integer `new_cap` strictly above 99, and no duplicate (`quest_key`, selector) pairs, failing
      closed on deviation

## 2. Sole cap writer

- [ ] 2.1 Implement `world/rules/affinity.py::raise_affinity_cap(npc, player, new_cap) -> bool`:
      creates a fresh record (value 0, cap 99) when none exists, monotonic raise only, value and
      daily-gain fields untouched, no budget logic and no auto-leave hook, returns whether the cap
      changed
- [ ] 2.2 Confirm serialization round trips preserve a raised cap (e.g. 150) with unchanged value
      and daily fields, including a fresh record created by the raise

## 3. Turn-in integration

- [ ] 3.1 In the deterministic guild-quest turn-in path, precompute `raise_affinity_cap` calls for
      every then-in-party companion matching a `cap_breaks` entry for the completed `quest_key`
- [ ] 3.2 Apply the cap raises **before** the `quest_completion` gains in the transaction, so a
      record at the old cap cannot clamp the +2; a companion matching multiple entries resolves to
      the highest `new_cap`
- [ ] 3.3 Commit the cap raises inside the existing atomic reward transaction, so a fault at any
      write position restores values and caps together

## 4. Tests

- [ ] 4.1 Pure/unit tests: `raise_affinity_cap` monotonic/idempotent/below-cap/record-creation
      behavior; `cap_breaks` load validation rejects each malformed shape (unknown quest, missing
      selector, duplicate quest+selector, `new_cap` <= 99)
- [ ] 4.2 `EvenniaTest` turn-in tests: matching entry raises caps for each matching companion in
      the same transaction; non-matching entry is a no-op; re-completed milestone is idempotent;
      value 99/cap 99 record ends at value 101 under the raised cap; recordless matching companion
      gets a fresh raised record plus the +2; overlapping entries resolve to the highest `new_cap`;
      fault injection restores caps and values
- [ ] 4.3 Ladder regression: a value above the old natural cap renders 絕對羈絆 with no numeric
      display
- [ ] 4.4 Regression: existing affinity, party-quest, and quest-reward-settlement suites stay
      green

## 5. Traceability and verification

- [ ] 5.1 Annotate the discoverable tests covering the new and modified requirements with
      `covers_requirement` using canonical IDs from
      `uv run --locked python -m tools.spec_traceability list`
- [ ] 5.2 Run `uv run --locked python -m tools.spec_traceability check` and confirm the
      affinity-cap-break, affinity-system, and quest-reward-settlement requirements are covered
- [ ] 5.3 Run the focused test packages (world rules and world quests tests) and confirm green
