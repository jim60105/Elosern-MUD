# Design: rename-reserve-to-energy

## Context

The term 精神儲備 reaches players from exactly four sources (observed with `rg -n "精神儲備"` outside `openspec/changes/archive/`):

- `web/webclient-app/components/StatusPanel.vue` line 78, the fatigue row template `{{ row.name }}：精神儲備 {{ row.reserve_percent }}%（{{ row.label }}）`.
- `world/rules/travel_cost.py` line 122, `DEPLETION_MESSAGE = "隊伍成員的精神儲備不足以支撐這趟旅行。"`, raised as the `MovementPreflightRefused` message for `pre_destination_depletion`.
- `world/rules/possession.py` `handoff_candidate_label`, the suffix `f"（精神儲備 {candidate.reserve_percent}%）"`. The browser roster shows the same server-authored label, so the client has no copy of this string outside test fixtures.
- `docs/game/commands.md` (lines 48, 57, 63, 78, 80) and `docs/game/command-reference.md` (lines 12, 190, 204, 233, 235, 349).

The other hits are comments or developer docs: `world/rules/fatigue.py` (module docstring), `world/rules/rulebook/buffs.yaml` and `combat_modifiers.yaml` (comments), `docs/development/distance-based-travel.md`, `docs/superpowers/specs/*.md`, and the prototype under `docs/design/time-choice-redesign/`.

## Goals / Non-Goals

**Goals:** replace 精神儲備 with 精力 in every string listed above and in the tests that assert them, and make 精力 unambiguous (user decisions, added after the first review):

- `滿儲備` in `docs/game/commands.md` line 63 and `docs/game/command-reference.md` line 190 would have no antecedent once 精神儲備 is gone, so it becomes 精力全滿, phrased `即使精力全滿，也不會…` so the clause reads naturally.
- `world/rules/service_messages.py` line 250 (`exam_started_message`) says `恢復全部的體力、法力與精力`, where 精力 meant SP. SP's UI name is 耐力, so the sentence becomes `恢復全部的體力、法力與耐力`. The function is shared by the text command (`commands/combat.py`) and the browser action (`web/webclient/actions/service_actions.py`), so one edit covers both clients. The only test asserting the sentence is `world/rules/tests/test_phase4_integration.py` line 223; no doc or main spec quotes it.

**Non-Goals:**

- Comments, docstrings, rulebook comments, identifiers, developer docs, and design docs keep 精神儲備 (design doc §9).
- Stage labels are unchanged.
- Other uses of the word 精神 (for example `精神恢復` in the combat paragraphs) are unchanged.

## Decisions

- **A plain string replacement, no shared constant.** The four sources are owned by different layers (Vue template, two rules modules, two Markdown files); a shared term constant would cross the client/server boundary for one word. Each source replaces the literal in place.
- **Docs grammar.** In the docs every 精神儲備 becomes 精力 with no other wording change; each resulting sentence reads naturally (for example `耗盡精力`, `生命、法力、體力與精力全滿`, `每秒 12 單位消耗精力`).
- **Test coverage for the travel message.** No test asserts the refusal text today. The task adds one assertion of `str(caught.exception)` to the existing `test_a_non_distance_connector_refuses_exhaustion_before_arrival` in `world/rules/tests/test_movement.py`, which already raises that refusal.
- **Traceability.** The new `mental-reserve` requirement has no canonical identifier until the archive syncs it. During apply, the touched tests keep their current annotations; at archive the travel, status-docs, and handoff tests are additionally annotated with the generated identifier (tasks.md group 5).

## Risks / Trade-offs

- [A missed occurrence leaves mixed terms] → the final task greps the player-facing files and the test files for 精神儲備 and expects no match.
- [Concurrent edits with `redesign-rest-entry` in the same two docs] → different lines; rebase is textual (see proposal Batch notes).
