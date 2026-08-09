# affinity-system

## Why

The master design declares `LivingEntity.relations` as an unassigned seam (§5.2) and whitelists the
`adjust_relation` NPC dialogue intent (§7.4), but no change owns either. The deterministic game has
no NPC-to-player affinity foundation, so the AI layer has nothing to consume (affinity deltas) and
no basis for later party invitations. This change lands that foundation: a hidden per-NPC numeric
affinity with a staged Traditional Chinese presentation, deterministic gains with a daily cap, and
the extensibility hooks (negative-delta path, per-record cap field, party auto-leave recheck call
site) that the follow-up `affinity-ai` and `party-*` changes rely on.

## What Changes

- **Mount `RelationHandler` on `LivingEntity.relations`.** The `None` placeholder seam becomes a
  working lazy-property handler (same pattern as `traits`/`buffs`/`sexual`); `persona` remains the
  only `None` placeholder seam. Storage is one tolerant-parsed serialized attribute per NPC, keyed
  by player primary key, with corruption recovery that resets to defaults instead of crashing;
  reads never materialize a record, so a mere look cannot create one.
- **Add a sole-writer affinity API.** `world/rules/affinity.py::apply_affinity_change(npc, player,
  source, delta)` is the only writer: a closed source set (`talk`, `trade`, `guild`,
  `ai_dialogue`, `quest_completion`) with unknown sources and non-NPC owners rejected; capped
  sources share a per-NPC daily budget of 5, lazily reset only before capped positive deltas;
  `quest_completion` is exempt; the applied delta is `min(requested, budget, cap - value)` and a
  zero-applied delta consumes no budget; negative deltas travel the same function (the future
  decrease-event path), never reset or restore budget, and trigger the party auto-leave recheck
  hook.
- **Add `rulebook/affinity.yaml`.** Exactly seven stages (初識 0 / 熟識 10 / 親睦 30 / 信賴 50 /
  羈絆 70 / 至愛 90 / 絕對羈絆 100), the offline party-invite threshold 70, the daily interaction
  cap 5, and the quest-completion gain 2 — each rule identified for one-to-one testing; loading
  validates the canonical floor sequence and fails closed on deviation.
- **Wire deterministic gains at existing success call sites.** Keyword talk +1 through a shared
  deterministic talk writer (committed atomically with any `guide_progress` update, cache
  restoration on failure), merchant buy/sell +1, guild registration/quest acceptance/rank exam +1
  — each committed all-or-nothing with the host operation's existing surfaces, through the
  sole-writer API; budget-capped gains present a fixed non-numeric Traditional Chinese hint.
- **Show the stage, never the value.** NPC appearance gains a stage line across all three entry
  paths (text look, `at_look`, webclient explore-look), rendered only when a record exists; the
  numeric affinity is never rendered.
- **Keep the cap-break and decrease extensions as data, not display.** The per-record `cap` field
  defaults to 99 and a future event can raise it; values above 99 map to the topmost stage
  automatically. No player-facing text mentions the cap.

## Capabilities

### New Capabilities

- `affinity-system`: The `RelationHandler` on `LivingEntity.relations`, the versioned per-NPC
  record store, the sole-writer `apply_affinity_change()` API with daily cap and negative-delta
  path, the `rulebook/affinity.yaml` stage ladder and balance numbers, deterministic gains at the
  talk/trade/guild call sites, the stage-only display contract, and the party auto-leave recheck
  hook.

### Modified Capabilities

- `living-entity-hierarchy`: The handler-seam requirement changes — `relations` becomes a working
  `RelationHandler` implementation while `persona` remains the only `None` placeholder seam, and
  the "no handler class authored" scenario narrows to `PersonaStore`.
- `scripted-dialogue`: The no-state-change contract gains an affinity exception — a successful
  known-keyword talk grants +1 affinity with the host through a deterministic talk writer that
  commits any `guide_progress` update and the gain in one transaction, while unknown keywords
  still write nothing.
- `shop-economy`: Trade settlement commits an additional surface — a successful buy or sell grants
  +1 affinity with the local Merchant host in the same transaction, and the trade snapshot/restore
  includes the host's affinity attribute.
- `guild-registration`: Registration additionally grants +1 affinity with the GuildStaff host,
  committed atomically with rank and snapshot (affinity joins the restore surfaces).
- `guild-quest-board`: Board acceptance additionally grants +1 affinity with the issuing host in an
  all-or-nothing operation with the quest record creation (quest-log, pin, and affinity surfaces
  snapshot and restore together).
- `guild-rank-exams`: A started rank examination additionally grants +1 affinity with the examiner
  inside the same atomic block that creates the exam record and session (the opponent stays
  pre-spawned per the existing contract); rejected starts grant nothing.
- `localized-appearance`: NPC appearance includes the affinity stage line, identical across the
  text look command, the `at_look` hook, and the webclient explore-look action.

## Impact

- **New code**: `world/rules/affinity.py` (handler + record + write API), `world/rules/rulebook/affinity.yaml`,
  `world/rules/tests/test_affinity*.py`.
- **Modified**: `typeclasses/entities.py` (relations seam), `typeclasses/tests/test_entities.py`
  (seam assertion), `commands/talk.py` / webclient talk-actions (talk gain), `world/rules/economy.py`
  (trade gain), `world/rules/guild*.py` (registration/board/exam gains), the appearance layer
  (`world/rules/appearance.py` or equivalent) for the NPC stage line, the seven modified delta specs.
- **Dependencies**: builds on `entity-traits` (the seam), `rulebook` (YAML engine), `world-clock`
  (day access for the lazy cap reset), `scripted-dialogue`, `shop-economy`, `guild-registration`,
  `guild-quest-board`, `guild-rank-exams`, `localized-appearance`.
- **Out of scope**: the `adjust_relation` AI intent activation and prompt injection (change
  `affinity-ai`), the party system (`party-*` changes), affinity decrease events, and cap breaks —
  their hooks are built and tested here, their triggers land later.
