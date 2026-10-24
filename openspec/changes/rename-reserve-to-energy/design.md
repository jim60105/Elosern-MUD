# Design: rename-reserve-to-energy

## Context

The term 精神儲備 reaches players from exactly four sources (observed with `rg -n "精神儲備"` outside `openspec/changes/archive/`):

- `web/webclient-app/components/StatusPanel.vue` line 78, the fatigue row template `{{ row.name }}：精神儲備 {{ row.reserve_percent }}%（{{ row.label }}）`.
- `world/rules/travel_cost.py` line 122, `DEPLETION_MESSAGE = "隊伍成員的精神儲備不足以支撐這趟旅行。"`, raised as the `MovementPreflightRefused` message for `pre_destination_depletion`.
- `world/rules/possession.py` `handoff_candidate_label`, the suffix `f"（精神儲備 {candidate.reserve_percent}%）"`. The browser roster shows the same server-authored label, so the client has no copy of this string outside test fixtures.
- `docs/game/commands.md` (lines 48, 57, 63, 78, 80) and `docs/game/command-reference.md` (lines 12, 190, 204, 233, 235, 349).

The other hits are comments or developer docs: `world/rules/fatigue.py` (module docstring), `world/rules/rulebook/buffs.yaml` and `combat_modifiers.yaml` (comments), `docs/development/distance-based-travel.md`, `docs/superpowers/specs/*.md`, and the prototype under `docs/design/time-choice-redesign/`.

## Goals / Non-Goals

**Goals:** replace 精神儲備 with 精力 in every string listed above and in the tests that assert them.

**Non-Goals:**

- Comments, docstrings, rulebook comments, identifiers, developer docs, and design docs keep 精神儲備 (design doc §9).
- Stage labels are unchanged.
- The related word 儲備 on its own (for example `滿儲備` in `docs/game/commands.md` line 63 and `docs/game/command-reference.md` line 190) is left as is: it is not the term 精神儲備, and in that sentence it can refer to all recovering resources. Changing it would widen the approved scope.

## Decisions

- **A plain string replacement, no shared constant.** The four sources are owned by different layers (Vue template, two rules modules, two Markdown files); a shared term constant would cross the client/server boundary for one word. Each source replaces the literal in place.
- **Docs grammar.** In the docs every 精神儲備 becomes 精力 with no other wording change; each resulting sentence reads naturally (for example `耗盡精力`, `生命、法力、體力與精力全滿`, `每秒 12 單位消耗精力`).
- **Test coverage for the travel message.** No test asserts the refusal text today. The task adds one assertion of `str(caught.exception)` to the existing `test_a_non_distance_connector_refuses_exhaustion_before_arrival` in `world/rules/tests/test_movement.py`, which already raises that refusal.
- **Traceability.** The new `mental-reserve` requirement has no canonical identifier until the archive syncs it. During apply, the touched tests keep their current annotations; at archive the travel, status-docs, and handoff tests are additionally annotated with the generated identifier (tasks.md group 5).

## Risks / Trade-offs

- [A missed occurrence leaves mixed terms] → the final task greps the player-facing files and the test files for 精神儲備 and expects no match.
- [Concurrent edits with `redesign-rest-entry` in the same two docs] → different lines; rebase is textual (see proposal Batch notes).
