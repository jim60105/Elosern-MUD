# Proposal

## Why

Every resolved action renders the same handful of shared sentences, and combat reads
like a mechanical ledger instead of a fight. Casting `挑逗=悠奈` prints
`悠奈 面對 悠花 的意圖，做出了自己的選擇。` / `悠花 的快感提升了。` /
`悠花 的性行為計數提升了。`; engaging a goblin prints
`哥布林 對 悠奈 的攻擊擲出了 92。` / `悠花 對 哥布林 造成了 450698 點傷害。` /
`悠花 消耗了資源。`. Nothing in the prose says *which* skill was used, every skill
reads identically, and raw rolls and damage numbers leak into the story channel.

The seam that causes this is one shared `text_template` per entry kind
(`world/rules/action/event_log.py::_ENTRY_TEMPLATES`), and a cast emits no
skill-action line at all. Fixing it once at that seam, deterministically and with
no model dependency, gives every later skill/act author a place to write prose.

## What Changes

- Add a frozen, authored narration catalog (new `world/skills/narration/` package)
  keyed by skill key and entry kind, validated fail-closed at import against the
  shipped skill/act registries; selection is a pure CRC-seeded pick over stable
  identifiers with no gameplay RNG, no clock read, and no network or model call.
- Rewire step 7 (`_step7_build_event_log`) so the first entry of a resolved action
  carries that skill's own action line composed with that entry's outcome clause,
  every later entry renders from a kind pool (shared, plus skill/act overrides), and
  a success that would otherwise print nothing emits one action line.
- Replace the number-bearing entry templates with numberless authored fallbacks.
  Rolls, damage, heals, resource amounts and pleasure gains become qualitative
  severity/outcome wording; `EventEntry.data` keeps every exact number, so quest,
  XP, loot, panel and OOB consumers are untouched.
- Narrate the combat prose that is not built by the action pipeline: the end-of-round
  upkeep tick lines, the skipped-action line, the party-retreat line, the overwhelm
  summary (whose counts leave the prose but stay in `data`), and the commanded-action
  marker.
- Rewrite the stable structural prose once — the round marker
  (`行動完成，繼續戰鬥。`), the terminal outcome announcements, and the engagement
  opening (`你向目標發起了攻擊！`) — as authored story lines that name the foe where
  one exists. These stay single stable lines on purpose (see design D10).
- Ship family-tier fallbacks (element × shape for elemental magic, line for sexual
  acts) so every one of the 223 ACTIVE skills narrates from day one, with an explicit
  exemption set that shrinks to empty in the three following changes. Per-skill and
  per-act lines are authored there; this change lands the engine, the shared prose,
  the combat prose, and the 42 non-elemental per-skill lines arrive in
  `narration-martial-and-mystery-skills`.

**BREAKING** for test expectations only: every test that pinned the removed generic
sentences must move to a mechanics assertion or to a constant, per the update policy
in design D12 (no repository has an external consumer of these strings).

## Capabilities

### New Capabilities
- `action-narration`: the authored narration catalog for resolved actions and combat
  rounds — its coverage and bounds contract, deterministic variant selection,
  qualitative severity bands, numberless prose, mechanical-entry pools, sexual
  verdict/role clauses, and the structural round/terminal/engagement lines.

### Modified Capabilities
- `event-log`: the entry text channel is authored narration rather than a shared
  template, while the entry payload and `render_entry_text`/`render_plain_text`
  purity stay exactly as they are.
- `action-resolution-pipeline`: step 7 selects narration for the log it builds,
  deterministically and without rolling, recomputing, mutating, rejecting, or
  changing entry kinds/order/data.
- `webclient-combat-beats`: every authored narration line is bounded by construction,
  so narration can never be the reason a settled round's beat panel is unavailable,
  and ordinary rounds keep exactly their current beat cardinality.

## Impact

- New package `world/skills/narration/` (vocab/bounds, catalog data modules,
  selector, validation).
- `world/rules/action/event_log.py` (step 7 narration pass, numberless fallbacks),
  `world/rules/combat/rounds.py` (skipped-action line, narration scope),
  `world/rules/upkeep.py` (end-of-round tick damage and defeat lines),
  `world/rules/combat_session/rounds.py` (party-retreat line),
  `world/rules/overwhelm.py` (summary + commanded-action prose),
  `world/rules/combat_result.py` and `world/rules/player_messages.py` (round marker,
  terminal announcements), `web/webclient/actions/exploration_actions.py` (engagement
  opening line through the shared catalog).
- Tests: two new `world/rules/tests/` modules registered in one shard, a new
  `world/skills/tests/` module covered by the existing `world.skills` shard label, and
  an updated coverage contract slice inside `world/skills/tests/test_skill_registry/`;
  exact-prose assertions in `test_combat_result.py`, `test_combat_actions.py`,
  `test_command_branch_behaviour.py`, `test_attribution_seam_and_command_surface.py`,
  `test_freeform_casting/test_text_commands.py`, `world/quests/tests/test_integration.py`
  and three browser modules' round-closing constants move to the policy in D12.
- No panel schema, OOB field, client protocol, command syntax, damage formula, or
  world-time change. No new dependency. `world/ai/narrator.py` is not wired in.

## Non-goals

- No LLM or network narration path: `world/ai/narrator.py` stays unwired and the offline
  template channel remains the only narration path.
- No webclient layout, panel schema, OOB payload or client-protocol change; no ANSI or new
  markup.
- No damage, healing, pleasure, cost or any other balance change; no RNG, timing or
  committed-state change.
- No player command key, alias, syntax or availability change (so `docs/game/commands.md`
  needs no update).
- No change to the observability event model.
- Item and consumable-use lines outside combat are out of scope: they are produced by the
  item settlement path, which this change does not narrate.
