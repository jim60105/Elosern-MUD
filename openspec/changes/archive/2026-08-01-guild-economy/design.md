## Context

Roadmap item 16 is the final deterministic-layer change before LLM integration. Change 15 supplies a
normalized quest runtime and a hand-written hunt through API-level tests, but deliberately leaves
player-facing acceptance, combat entry, turn-in, rewards, guild progression, and inventory-backed
ACQUIRE progress to this change. The landed repository already supplies:

- `PlayerCharacter.guild_rank`, `wallet`, and `quest_log` persistent seams;
- `guild_merit` as an unbounded CounterTrait and F-through-S lore entries with copper reward bands;
- integer-copper conversion and purchasing-power reference ranges;
- a flat persistent item-key inventory and deterministic add/remove operations;
- a complete action/combat engine, but no command that starts a battle or advances one player-selected
  combat round;
- `caravan_arrivals` and `shop_hours` in the fixed clock settlement order, both still unregistered;
- component-capable LivingEntity typeclasses, but no project-authored service components; and
- an Altoria street map whose guild and shops are exterior descriptions only.

The owner approved a mandatory combat examination after each merit threshold, finite merchant stock
with clock-driven restocking, F-rank entry for every new registrant, and a callable exam trigger that
future validated AI intent may reuse. The project is unreleased, so the proposal optimizes the model
directly rather than preserving placeholder data shapes.

## Goals / Non-Goals

**Goals:**

- Deliver a complete command-level, no-LLM register-to-rank-promotion loop.
- Preserve the deterministic writer boundary: service components and commands adapt inputs, while
  `world/rules/` and the quest owner apply state.
- Keep all money integral copper and all multi-surface payouts/trades atomic and cache-consistent.
- Make guild registration the first implemented consumer of `get_display_value()` without allowing disguise
  data into combat or promotion resolution.
- Add an interactive, persistent player combat session over the landed combat primitives.
- Keep examination initiation callable by a future validated intent without importing AI code.
- Activate finite stock, opening hours, and caravan restocking through the existing clock order.
- Add ACQUIRE progress only at committed inventory-delta boundaries.

**Non-Goals:**

- No AI client, dialogue parser, autonomous trigger policy, or direct `world/ai/` integration. Change 19
  owns intent extraction; this change only defines the deterministic target API.
- No procedural quest, examiner, merchant, item, or shop generation.
- No auction house, player-to-player trade, crafting, durability, item use effects, equipment stat
  bonuses, variable bargaining, credit, debt, tax, or denomination objects.
- No party combat or companion quest credit. The product remains single-player.
- No direct rank placement from visible or true stats. Every registration starts at F.
- No migration or compatibility layer for placeholder `guild_rank`/`wallet` values.

## Decisions

### D-1. Static definitions are immutable; deterministic rules own every write

`world/lore/items.py` and `world/lore/shops.py` define frozen, deeply immutable item, shop, and offer
records. Existing `GUILD_RANK_REGISTRY`, `PRICE_TABLE`, and quest definitions remain source registries.
Tunable hand-written quest rewards, merit thresholds, examiner combat profiles, opening times, exact
prices, buyback values, stock caps, and restock quantities live in
`world/rules/rulebook/guild_economy.yaml`.

Mutation is divided by existing ownership:

- `world/quests/` remains the sole owner of quest-record transitions and computes ACQUIRE replacement
  records from a proposed inventory delta.
- `world/rules/guild.py` owns registration, rank, merit eligibility, board access, and reward claims.
- `world/rules/economy.py` owns wallet, inventory, and merchant-stock transactions.
- `world/rules/guild_exams.py` owns exam eligibility, lifecycle, outcome, and promotion.
- `world/rules/combat_session.py` owns persistent player combat-session orchestration.

`GuildStaff`, `Merchant`, and `GuildExaminer` components contain identifiers and persisted service data,
not business-rule methods. Commands locate a component-bearing host in the caller's room and invoke a
rules API. This keeps future NPC dialogue and present commands as equal adapters.

Alternative rejected: implementing buy, turn-in, or promotion on the NPC component. That would make a
presentation/typeclass adapter a second writer and make future AI intents bypass command-only checks.

### D-2. Registration always grants F and snapshots only displayed values

`register_adventurer(actor, staff)` accepts an unregistered PlayerCharacter standing with a
`GuildStaff` host. It derives `branch_key` exclusively from that validated component, reads all eight
trait keys through `get_display_value()`, and writes:

```python
actor.db.guild_registration = {
    "branch_key": "guild_branch_altoria",
    "registered_tick": 1234,
    "displayed_stats": {
        "hp": 100,
        "mp": 100,
        "sp": 100,
        "atk_phys": 8,
        "agility": 9,
        "defense": 7,
        "magic_level": 20,
        "guild_merit": 0,
    },
}
actor.guild_rank = "F"
```

The snapshot is historical and never refreshed automatically. Every registrant starts at F regardless
of the snapshot. Repeating registration for an already registered actor is an idempotent read that does
not overwrite the original branch, tick, or displayed values. A malformed partial registration raises
`GuildDataError` rather than being repaired silently.

Combat, exam eligibility, and examiner scaling never call `get_display_value()`. They read canonical
rank, merit, and true traits. Registration therefore implements D2's promised consumer without turning
the disguise into a resolution system.

Alternative rejected: assign an initial rank from displayed power. The owner selected universal F-rank
entry, and world lore requires both merit and examination for advancement.

### D-3. Guild offers bind economics to quest definitions without moving quest state

`world/rules/guild_offers.py` defines immutable `GuildQuestOffer` and `QuestReward` records:

```python
@dataclass(frozen=True)
class ItemQuantity:
    item_key: str
    quantity: int

@dataclass(frozen=True)
class QuestReward:
    copper: int
    items: tuple[ItemQuantity, ...]
    merit: int

@dataclass(frozen=True)
class GuildQuestOffer:
    definition_key: str
    issuer_branch_key: str
    reward: QuestReward
```

Registration rejects unknown quest/item/branch keys, non-positive item quantities, negative reward
fields, duplicate item keys, a mismatch between offer and quest rank, and copper outside that rank's
`GuildRank` reward band. S rank accepts any value at or above its open minimum. Equal duplicate
registration is idempotent; conflicting registration fails before replacement. Hand-written offer
reward values load from `guild_economy.yaml`; future validated AI offers construct the same immutable
type only after semantic validation.

Keeping reward/issuer data in the guild offer avoids making the generic quest state machine own wallets
or branches. Change 20 can translate a validated AI blueprint into both a `QuestDefinition` and a
`GuildQuestOffer`; neither runtime accepts the raw AI mapping.

The board lists only offers issued by the local branch whose quest rank order is no greater than the
actor's canonical guild-rank order. Accept delegates to change 15's `accept_quest()`. Abandon delegates
to `abandon_quest()`. Unregistered actors, unknown offers, over-rank offers, and remote staff fail with
named reasons and no quest mutation.

### D-4. Reward claims are keyed by quest ID and settle all surfaces once

Change 15 retains completed quest records as history and permits later acceptance numbers. Reward claim
state is therefore a separate JSON-safe `actor.db.guild_reward_claims` list of deterministic quest IDs,
not a fourth quest state. `turn_in_quest(actor, staff, quest_id)` requires:

1. a valid guild registration and local GuildStaff;
2. a parsed `COMPLETED` record with the exact quest ID;
3. a registered offer for that definition and the staff's branch; and
4. the quest ID absent from reward claims.

It precomputes the new wallet, repeated-key inventory list, guild-merit counter value, ACQUIRE quest-log
replacement, and claims list. One `transaction.atomic()` block then writes all surfaces. A fault after
any write restores every Evennia attribute/trait cache to its pre-call value. The quest history remains
`COMPLETED`; the claim list distinguishes paid from unpaid completion and permits each later acceptance
number to earn its own reward exactly once.

Reward item acquisition may progress other active ACQUIRE objectives in the same transaction. It never
reopens or changes the completed quest being claimed. Copper and merit are non-negative integers; wallet
underflow and floats are rejected at every public boundary.

Alternative rejected: add `TURNED_IN` to `QuestState`. Reward claim is branch/economy metadata, and
forcing it into generic quest lifecycle would couple non-guild quests to a guild payout concept.

### D-5. ACQUIRE progress observes committed inventory deltas, never caller assertions

Change 16 extends `ObjectiveKind` with `ACQUIRE`. An ACQUIRE objective declares one known `item_key` and
a positive quantity, with no destination, monster selector, or runtime entity binding. The accepted
record uses existing `stage_progress`.

`world/rules/equipment.py` replaces direct list writes with a staging API:

```python
plan_inventory_delta(entity, additions=(), removals=()) -> InventoryPlan
apply_inventory_plan(plan) -> None
```

The planner validates item keys structurally (each key is a non-empty string, so unregistered but
syntactically valid keys such as the spec scenario's `iron_ore` remain acceptable), positive quantities,
and sufficient removals. Known-item identity is enforced at the boundaries that reference the lore
registry — ACQUIRE objective definitions, rewards, and shop offers validate against `ITEM_REGISTRY` —
while the flat inventory itself remains an open repeated-key list. The planner asks the quest
runtime to compute progress only from the plan's positive additions. Shop purchases and reward claims
include that replacement quest log in their surrounding transaction. `add_item()` and `remove_item()`
remain convenience wrappers over the same planner, so no deterministic inventory producer can omit the
hook. A failed or rolled-back plan produces no progress. Removal and sale never reverse progress.

One delta can advance multiple active quests, but each quest advances at most one stage and discards
surplus according to change 15's event semantics. Item additions caused by import loading are initial
state, not gameplay acquisition, and continue to write raw inventory during object construction without
progress.

Alternative rejected: a public `observe_item_acquired(item_key, qty)` call. It could be invoked without
an inventory write and forge quest completion.

### D-6. Player combat sessions persist dbrefs and consume one chosen action per round

The combat engine already supports `Battlefield`, `run_round()`, monster policies, fleeing, and
overwhelm resolution, but `CmdCast` currently resolves immediately without driving opponent turns.
`world/rules/combat_session.py` adds a JSON-safe `CombatSessionRecord` under
`PlayerCharacter.db.active_combat`:

```python
@dataclass(frozen=True)
class CombatSessionRecord:
    session_id: str
    mode: str                 # hostile | guild_exam
    room_id: int
    player_ids: tuple[int, ...]
    enemy_ids: tuple[int, ...]
    fled_ids: tuple[int, ...]
    knocked_out_ids: tuple[int, ...]
    rounds_elapsed: int
    exam_id: str | None
```

`engage <target>` validates a living hostile target in the same room, no active session, and an unsafe
location appropriate for combat. It captures all explicitly selected combatants, creates the record,
registers the reconstructed Battlefield with skip safety, records the initial overwhelm classification,
and always prompts for the player's first action. It never runs a round before that input.

During an active session, `cast <skill>=<target>` builds exactly one player `ActionRequest` and first
calls a new side-effect-free `ActionResolver.preflight()` seam. Preflight performs ownership, resource,
target, capability, effect-handler, and time-metadata validation without rolling, staging effects,
committing state, or emitting an EventLog. A preflight rejection occurs before initiative, so no NPC
acts, no upkeep runs, and no round is consumed. Once preflight succeeds the round has begun: a later
ActionResolver rejection caused by an earlier initiative action is a consumed round, because preceding
NPC effects cannot be undone.

For an ordinary round, a session provider returns the queued request once for the player and the landed
monster policy for each enemy, then `run_round()` handles initiative and upkeep. A successful round
replaces the session record with updated fled/knockout state and round count. When initial or recomputed
classification is overwhelming, the first preflight-valid player request becomes the input to
`resolve_overwhelm()`: it is used exactly for the first simulated player turn, and subsequent compressed
player turns use deterministic `basic_attack` against the lowest-HP living enemy. This is the explicit
input-compression exception to per-round choice; no overwhelm work runs before the player selects the
first action.

World time is not advanced per in-session cast. Out-of-combat CmdCast retains its existing command time.
When battle ends, accumulated rounds settle once through `settle_combat_result()`, matching design §6.3.
Flee, player defeat, enemy defeat, forfeit, invalid recovery, and the round cap settle named outcomes and
clear stale action contexts.

`basic_attack` is a zero-cost SINGLE/ENEMY active skill with the ordinary physical damage effect. It is
added beside `flee` in `INNATE_SKILL_KEYS`, so every LivingEntity can participate even without imported
skills. It still passes skill ownership, targeting, ActionResolver, modifiers, EventLog, and quest
planners. It has no out-of-combat use.

Active combat is persistent rather than `ndb`-only. A PlayerCharacter with an active session cannot
traverse an exit or otherwise leave the recorded room; it must win, lose, use the existing flee action,
or explicitly `combat forfeit`. Disconnect does not advance a player-driven world and therefore pauses
the session; reconnect reconstructs it. Forfeit records ordinary defeat or exam FAIL, settles accumulated
time, removes an exam opponent when applicable, and clears session/skip-safety state. Startup reconstructs
valid sessions; invalid/deleted/moved participants terminate an ordinary session diagnostically or settle
an examination as FAIL, so neither path leaves the player blocked or an opponent orphaned.

Alternative rejected: a command that calls `run_battle()` to completion using automatic player policy.
That would satisfy reachability superficially but contradict the approved player-waits-for-input loop.

### D-7. Guild examinations are ordinary combat with a nonlethal terminal policy

`start_guild_exam(actor, examiner, target_rank, *, requested_by)` is the only examination trigger. Its
`requested_by` value is audit metadata (`"command"` now, `"npc_intent"` later), never authority. The
function itself validates:

- actor and examiner are present together and the examiner has `GuildExaminer` for the branch;
- actor is registered, has no active combat/exam, and requests exactly the next rank;
- actor's true `guild_merit` meets the target rank's YAML threshold; and
- no prior passed result for the same promotion exists.

It creates a deterministic `GuildExamRecord` with ID `<character-id>:<target-rank>:<attempt-number>`,
spawns a temporary adult NPC opponent from the target rank's whitelisted exam profile into the permanent
exam hall, and starts `CombatSessionRecord(mode="guild_exam")`. Profiles map E/D to the human-adventurer
band, C/B to human-elite, A to human-veteran, and S to human-swordmaster; exact true stats and skills are
YAML values validated inside those lore bands. No displayed stat influences this opponent.

Opponent spawn, exam-record creation, and combat-session creation are one all-or-nothing start operation;
any failure restores caches and deletes an already-created temporary opponent.

Examination combat uses the same action and round path, with a `nonlethal=True` policy in the
BattlefieldActionContext. Damage projection applies that policy before EventLog construction or any
event-effect planner: a lethal crossing stages HP floor 1 and `target_knocked_out`, never
`target_defeated`. Consequently kill XP, DEFEAT progress, protected-entity failure, and loot consumers
have no ordinary defeat event to observe. Spent MP/SP, buff ticks, and sexual-state transitions remain
real costs. Ordinary hostile contexts retain existing lethal behavior. The temporary opponent is deleted
at settlement.

If the opponent is knocked out, one atomic settlement records PASS, advances `guild_rank` exactly one
step, and closes the exam. If the player is knocked out, flees, explicitly forfeits, has an invalid
session at recovery, or reaches the configured round cap, it records FAIL and leaves rank/merit
unchanged. A disconnect alone pauses and later resumes the persisted attempt. Merit is cumulative and is
not spent. Replaying settlement is idempotent by exam ID.

This API is the future-AI seam. Change 19 may validate an NPC dialogue
`{"kind":"request_guild_exam","target_rank":"E"}` intent and call it with
`requested_by="npc_intent"`; the intent cannot waive presence, examiner capability, next-rank, merit,
or active-session checks. Illegal intent is discarded while speech remains, following §7.4.

Alternative rejected: auto-promote at the threshold. World lore explicitly requires merit plus a guild
examination, and the owner selected a combat exam.

### D-8. Shops use finite repeated-key stock and exact integer prices

`ItemDefinition` gives each supported item a stable key, Traditional Chinese display name, price-table
reference, and sellability. `ShopDefinition` gives a shop stable identity, merchant component key, and
immutable offered item keys. Both are Python lore registries. Initial content includes an ordinary meal,
healing potion, and plain sword. Item use/equipment effects remain out of scope; the keys are still valid
inventory values.

`guild_economy.yaml` supplies each shop's opening/closing hour, restock hour, and rule entries carrying
exact `buy_copper`, `sell_copper`, `max_stock`, `initial_stock`, and `restock_quantity`. Loading joins
those rules to the immutable lore definitions and rejects missing/extra items. Validation requires
integer non-negative prices, `sell_copper <= buy_copper`, a buy price within the referenced
`PRICE_TABLE` band, and bounded positive stock values. No percentage or floating-point buyback
calculation occurs at runtime.

The Merchant host persists `merchant_stock` as `{item_key: quantity}` and `last_restock_day`. `buy()`
and `sell()` require a positive integer quantity, an open local merchant, a known offer, and complete
fund/stock/inventory availability. They precompute wallet, inventory, ACQUIRE quest progress, and stock,
then commit all surfaces atomically with cache restoration. Buying decrements stock and copper; selling
increments stock and copper but rejects quantities that exceed `max_stock`. Wallet can never become
negative.

Opening status is derived from WorldClock calendar and supports an overnight interval even though the
initial shop uses a same-day interval. The `shop_hours` event source emits JSON-safe open/close events for
every crossed boundary but stores no redundant open boolean. `caravan_arrivals` applies one restock per
crossed daily restock boundary, catches up across multi-day skips up to each cap, updates
`last_restock_day`, and emits one event per merchant/day. Existing stage order means stock arrives before
that day's shop-opening event.

Alternative rejected: infinite stock. The owner selected finite stock plus restocking, and the clock
already reserves the required deterministic stages.

### D-9. Service content is idempotently synchronized into permanent Altoria interiors

The thirteen-node xyzgrid street topology remains unchanged. Map bootstrap additionally creates two
ordinary permanent `Room` interiors with stable tags:

- `altoria_guild_hall`, linked bidirectionally to the existing adventurers' guild exterior; and
- `altoria_general_store`, linked bidirectionally to the existing blacksmith/market exterior.

The guild hall contains one adult NPC host with `GuildStaff` and `GuildExaminer`, plus a deterministic
exam-opponent spawn point. The store contains one adult NPC host with `Merchant`. All rooms, exits,
components, stock initialization, and NPCs update in place by stable key/tag; repeated startup creates
no duplicates and does not reset live stock or registration data.

`commands/guild.py`, `commands/combat.py`, and `commands/economy.py` provide concise Traditional Chinese
output with English aliases. A service command searches only the caller's current room and rejects zero
or ambiguous matching component hosts. No global dbref may be supplied to interact remotely.

Alternative rejected: place all service NPCs on exterior streets to avoid modifying the map. Permanent
interiors are required for a coherent playable guild/shop path and do not disturb xyzgrid topology.

### D-10. Cross-surface operations share preflight, transaction, and cache restoration rules

Reward claim, purchase, sale, registration, exam settlement, and ACQUIRE progress follow one order:

1. Parse every persisted record and resolve every registry key.
2. Validate authorization, location, quantities, balances, stock, rank, and state transition.
3. Compute complete immutable replacement values without writes.
4. Snapshot every touched AttributeProperty, raw Attribute, trait, component field, quest log, and
   session surface.
5. Apply all writes in one `transaction.atomic()` block.
6. On any exception, restore in-process caches after database rollback and raise a named domain error.

Commands render known domain errors and never expose a partial success. Clock restocking isolates a
malformed merchant at the host boundary, reports a diagnostic, and continues other merchants without
changing the malformed host. No operation silently clamps funds, stock, merit, or quantities.

### D-11. Startup registration and offline acceptance test establish the Phase-4 milestone

Server startup runs lore/map synchronization, quest synchronization, then
`sync_guild_economy()`. The final function validates catalogs, installs components/content
idempotently, registers `caravan_arrivals` and `shop_hours`, and restores combat/exam sessions. It does
not import `world/ai/` or call an external service.

The command-level integration test starts with an unregistered character and all LLM profiles failing.
It walks into the guild hall, registers at F, lists and accepts the hand-written hunt, uses `engage` and
`basic_attack`/`cast` through at least one real combat round, observes automatic quest completion,
returns to claim copper/items/merit, buys an item, crosses a closed/open/restock boundary, repeats enough
fixed quests to meet E-rank merit, starts a nonlethal exam, defeats the examiner, and observes E rank.
Fixed dice and compact test-only YAML/profile overrides keep it deterministic without bypassing any
production entry point.

## Risks / Trade-offs

- **[Risk] Change 16 depends on change 15 artifacts that were proposed when this design was drafted.** →
  Change 15 has since been implemented and archived; all integration stays through the published quest
  APIs, and this implementation began only after change 15 passed strict verification.
- **[Risk] Persistent combat sessions refer to deleted or moved entities.** → Store dbrefs, validate room
  and liveness on every action/startup, and terminate invalid sessions with a diagnostic and clock-safe
  cleanup.
- **[Risk] Examination combat could leak ordinary rewards or quest credit.** → Carry an explicit
  nonlethal mode through damage/EventLog planning and test every kill-credit, quest, failure, XP, and
  loot consumer against it.
- **[Risk] Multi-attribute Evennia caches can disagree with a rolled-back database.** → Centralize
  snapshots/restores and fault-inject every write position in reward, trade, exam, and stock settlement.
- **[Trade-off] Registration snapshots displayed values but every actor starts at F.** → This preserves
  D2's narrative record while following the owner-approved progression rule.
- **[Trade-off] Merit is cumulative rather than spent on promotion.** → Rank thresholds describe earned
  reputation; mandatory exams provide the second gate without making rank loss possible through payout.
- **[Trade-off] Initial items have economic identity without use effects.** → Phase 4 proves inventory
  and prices; consumable/equipment behavior requires a separately specified item-effect system.
- **[Risk] Multi-day restock catch-up could generate excessive events.** → Apply bounded arithmetic per
  crossed day and cap stock; tests cover large skips without per-second iteration.

## Migration Plan

No migration or backward-compatibility code is required. The project is unreleased and the affected
guild/economy fields are documented placeholders with no shipped data. Fresh startup idempotently
creates the service content and initializes only missing merchant stock.

## Open Questions

None. Exact initial merit thresholds, exam stats, stock, hours, and prices are implementation-owned YAML
values constrained by this design and the lore registries; they remain tunable without changing the
state-machine contracts. Future change 19 owns extraction of `request_guild_exam`, while this change owns
all legality and mutation after such a request.
