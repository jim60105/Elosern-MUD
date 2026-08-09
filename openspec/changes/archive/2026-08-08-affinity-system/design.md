# affinity-system Design

## Context

The master design (§5.2) declares `LivingEntity.relations` as a deferred seam and whitelists the
`adjust_relation` NPC dialogue intent (§7.4), but nothing owns either. The deterministic game needs
the NPC-to-player affinity foundation before the generative layer can consume it. This change is the
first of six sliced changes (see `docs/superpowers/specs/2026-08-08-affinity-party-design.md`):
it delivers the record store, the stage ladder, deterministic gains, and the display contract,
together with the hooks the follow-up changes consume (negative-delta path, per-record cap field,
party auto-leave recheck call site).

Constraints: single-player (one player in practice, but the codebase must not assume a singleton),
no released users (no migrations or compatibility layers), single-writer invariant (no module
outside the deterministic core writes affinity; the generative layer consumes it only through
`adjust_relation` in a later change), all-or-nothing commits at existing call sites, and full
offline determinism.

## Goals / Non-Goals

**Goals**

- Fill the `relations` seam with a working, persistence-safe `RelationHandler`.
- One deterministic write API with a daily cap that resets by world-day without touching the
  load-bearing clock settlement order.
- A YAML stage ladder and balance table following the rule-ID/test-ID pairing convention.
- Gains at the existing talk / trade / guild success paths, committed atomically with the host
  operation's existing surfaces.
- Stage-only display on all three appearance entry paths; the numeric value never rendered.
- The three forward hooks (negative delta, cap break, auto-leave recheck) built and tested now,
  triggered later.

**Non-Goals**

- AI deltas (`adjust_relation` activation) and prompt injection — change `affinity-ai`.
- Party invitations, membership, follow, combat, quest assistance — `party-*` changes.
- Affinity decrease events and cap-break events — future triggers use the hooks built here.
- Any player-facing numeric display or a dedicated affinity-query command.

## Decisions

### D-1: Affinity is owned by the NPC, stored as a keyed serialized attribute

`npc.db.relations_data = {str(player_pk): {"value": int, "cap": 99, "daily_gain": int, "daily_tick": int}}`.
`RelationHandler` is a `@lazy_property` mounted on `LivingEntity.relations`, replacing the
`AttributeProperty(default=None)` placeholder. Reads (`affinity_for`, `stage_for`) return defaults
without persisting anything; `has_record(player)` is the only way to distinguish a stored record —
so a mere look never materializes an affinity record. `persona` remains the only `None` placeholder
seam; the other handlers (`traits`, `sexual`, `buffs`, `equipment`, `skills`) are already working
implementations and are untouched.

Why NPC-side rather than player-side: affinity is the NPC's emotion; NPC-side behavior (prompt
injection, future party/combat reads) reads its own attribute with no cross-entity lookup, and the
seam is declared on the entity. A player-side dict only wins for whole-matrix listing, which this
game never renders (players see only co-located NPCs). A dedicated Django model wins on multi-player
scale and indexed queries but introduces a storage pattern this codebase has never used for entity
state (quest records, inventories, chat memory are all attributes) — overkill for a sparse matrix
that is a vector in practice. Escape hatch: if multi-player ever lands, migrating the dict to a
`(npc, player)` Django model is a data migration, not a design change; the record and API shape
survive.

Alternatives considered: player-side dict (rejected: semantic inversion, cross-entity reads),
Django model (rejected: new pattern, no scaling need), per-entity attribute per player key
(rejected: attribute explosion).

### D-2: One writer, one transaction per call

`apply_affinity_change(npc, player, source, delta)` is the only affinity writer. `source` must be
a member of the closed set (`talk`, `trade`, `guild`, `ai_dialogue`, `quest_completion`); an
unknown source or a non-NPC owner returns a rejected outcome and writes nothing. The applied delta
is `min(requested, remaining_budget, cap - value)` for capped positive deltas, `quest_completion`
and negative deltas bypass the budget, and the daily counter accrues only the actually applied
increase — a zero-applied delta consumes no budget. The party auto-leave recheck runs after every
negative delta (a no-op today: no decrease events exist).

Callers (talk, trade, guild functions) call it inside their existing all-or-nothing commits and
extend their snapshot/restore surfaces with the host's `relations_data` attribute, so a failing
host operation restores the affinity surface alongside the others (mirroring the cache-restoration
idiom in `world/rules/economy.py` / `npc_intents.py`). The API returns a structured outcome
(applied / capped / rejected) so callers can render feedback; a budget-capped gain presents a
fixed non-numeric Traditional Chinese hint and never exposes the cap or any number. The AI-side
caller (`adjust_relation`, change 2) uses the same outcome to report a rejected delta while
keeping the speech.

### D-3: Daily cap resets lazily by world-day, only before capped positive deltas

The record stores the world-day tick at which `daily_gain` started; before budgeting a capped
positive delta, a caller whose tick differs resets the counter. Negative deltas never reset the
counter and never restore spent budget. This avoids registering a settlement source in the clock's
fixed settlement order (regen → buffs → sexual → resets → world events), which is load-bearing and
owned by another change. Deterministic, single-attribute read, no timer.

### D-4: Ladder and balance numbers are rulebook YAML

`rulebook/affinity.yaml` holds `invite_threshold: 70`, `daily_interaction_cap: 5`,
`quest_completion_gain: 2`, and exactly seven stage rules (初識 0 / 熟識 10 / 親睦 30 / 信賴 50 /
羈絆 70 / 至愛 90 / 絕對羈絆 100), each with an ID, a floor, a display name plus a per-stage
flavor line template for `look`. Stage resolution is "last stage with `floor <= value`"; values
at or above 100 resolve to the topmost stage, which is reachable only after a future cap break.
Loading validates the canonical floor sequence exactly (seven stages, floors
0/10/30/50/70/90/100, strictly increasing, no duplicates) and fails closed on any deviation.
Traditional Chinese glyphs (信賴, 絕對) are the player-facing forms.

Why YAML: balance numbers are data (D9), and the rule-ID/test-ID pairing gives one test per stage
and per constant, consistent with `sexual.yaml` and `combat.yaml`.

### D-5: Gains are wired at the existing deterministic success paths

- Talk: a new deterministic talk writer (shared by `commands/talk.py` and webclient
  `explore.talk_scripted`) resolves the keyword through the dialogue service (known vs unknown),
  snapshots the player's `guide_progress` and the host's affinity record, applies the authored
  response plus any `guide_progress` update plus the +1 gain inside one transaction, and restores
  both surfaces on failure. Unknown keywords and no-keyword paths grant nothing. AI freeform talk
  grants no fixed value (its `adjust_relation` delta is change 2).
- Trade: `buy()` / `sell()` success grants +1 with the local Merchant host; the trade snapshot
  (`_snapshot_trade` in `world/rules/economy.py`) gains the host's `relations_data` surface and
  the restore path restores it.
- Guild: `register_adventurer()` success, `accept_guild_offer()` success, and a started
  `start_guild_exam()` each grant +1 with the respective host. Registration and exam extend their
  existing snapshot surfaces with the host's affinity record. `accept_guild_offer()` gains an
  outer all-or-nothing commit: snapshot of the actor's quest-log surface plus the host's affinity
  record (acceptance creates no instance pins — stage binding happens only on stage advance),
  then `accept_quest()` and the gain inside one transaction, with restore on
  failure (mirroring the `npc_intents` transfer pattern). For the exam, the affinity gain joins
  the same atomic block that creates the record and session (the opponent is pre-spawned before
  any mutation, per the existing contract).

Each call site is a thin wrapper around the sole-writer API; no call site writes state itself.
Service hosts must be NPC instances: a host that cannot hold affinity is rejected before any write
(a non-NPC Merchant/GuildStaff/GuildExaminer holder is invalid), so a successful operation always
carries its gain and a rejected writer outcome is unreachable at these call sites.

### D-6: Display goes through the appearance layer

NPC appearance gains a stage line (e.g. 「她看著你的眼神裡帶著信賴。」) rendered by the shared
appearance layer so text look, `at_look`, and webclient explore-look stay byte-identical, matching
the `localized-appearance` contract. The line reads `has_record(player)` first and renders
`stage_for(player)` only when a record exists; the read never persists. The numeric value never
appears in any frame. No dedicated command.

### D-7: Tolerant serialization with corruption recovery

`to_storage` / `from_storage` mirror the `QuestRecord` idiom: tolerant field parsing, defaults for
missing fields, rejection of type-violating records (reset to a fresh record + log, never crash a
look or talk). The `cap` field already serializes so a future cap-break event only mutates one
number per record. Record-shape evolution is handled by the tolerant parser; no explicit version
field is carried.

## Risks / Trade-offs

- [A corrupted or maliciously shaped `relations_data` attribute crashes appearance/dialogue] →
  `from_storage` validates every field; invalid records reset to defaults and log, matching the
  quest-record idiom.
- [A call site forgets the affinity commit, silently diverging from the spec] → every capped
  source is a named constant; each call site gets a focused test asserting the gain and the
  atomicity (fault injection restores the affinity surface too).
- [The talk path loses atomicity with `guide_progress`] → the deterministic talk writer owns the
  single transaction and the dual-surface snapshot/restore; both entry paths (text command and
  web action) call it, and a fault-injection test pins the restore.
- [`accept_guild_offer` gains a transaction layer it lacked, risking quest-log cache drift] →
  the acceptance snapshot includes the quest-log surface (the `npc_intents` transfer idiom already
  does this); a fault-injection test pins all surfaces.
- [Exam-start affinity wording misstates the pre-spawned opponent] → the delta says "same atomic
  block as the record and session", not the opponent; no refactor of the existing spawn ordering.
- [Daily-cap semantics drift from the world-day] → the lazy tick comparison is tested with two
  explicit cases: same-day budget exhaustion and cross-day reset, plus partial-delta and
  zero-applied-no-budget boundaries.
- [Stage YAML and the hard-coded 99 natural cap diverge] → the cap lives in the record default,
  the ladder loader validates the canonical floor sequence; a test pins both.
- [Appearance changes break the three-path identity contract] → the stage line is rendered by the
  shared layer; existing three-path parity tests extend with an NPC carrying an affinity record,
  and a recordless entity renders no line (and persists nothing).

## Migration Plan

No released users: no data migration. Existing NPCs gain `relations_data` lazily on first write
(the handler creates the record on demand). The seam test in `typeclasses/tests/test_entities.py`
is updated in this change. Rollback is a revert of the change; no stored data depends on the
attribute existing.

## Open Questions

- None blocking. Whether the stage line should render for every NPC (including monsters, which
  share `LivingEntity`) is decided: NPCs only — monsters carry no affinity records and the layer
  renders the line only when a record exists.
