# Quest Issuer Model, Delivery, and Host-Free Reference Drawers — Design

**Date:** 2026-09-06
**Status:** Approved (brainstorming session 2026-09-06)
**Scope:** Generalizing quest issuance from "guild-only" to an issuer layer that also covers
world/NPC-issued commissions with automatic settlement; adding a deterministic delivery objective
and player action; two new host-independent read models (`quest_log`, `lore_codex`); the quest
drawer split; deterministic lore-reveal sources; and relocating the codex trigger out of the quest
drawer into `.cmdutil`.

---

## 1. Product Context

Two player-facing defects started this work:

1. **The quest drawer is empty away from a guild clerk.** The `任務` dock tab is always present in
   exploration mode (`exploration.quests.available` mirrors whether the services view can be built,
   which needs no host), so the drawer opens anywhere — but `QuestBoard.vue` reads only
   `services.guild`, and `_build_guild()` returns `None` without a local `GuildStaff`. The player
   sees `尚未取得公會資料`. Quest details are handed to the player at acceptance; reading one's own
   quest log is not a counter service.
2. **The `世界圖鑑` button does nothing useful.** It opens `LoreDrawer.vue`, which despite its name
   renders guild quest prose from the `services` payload — its own header comment admits the
   8-category codex "has no OOB read model in this payload... a deliberate skip". The codex backend
   is fully implemented; only the read model and UI are missing. The button also does not belong in
   the quest drawer: the codex is not a guild service.

Investigating (2) surfaced a third, larger requirement: **quests should not be guild-bound.** A
shopkeeper handing the player a delivery run, or a clue that completes on arrival, is a world side
quest. It belongs in the same quest log, managed in the same drawer, but it is not a guild
commission and it settles itself on completion rather than at a counter.

## 2. Decision Summary

| Decision | Choice | Rationale |
|---|---|---|
| Where issuance lives | New `QuestIssuance` registry keyed `(definition_key, issuer_key)` | Direct generalization of today's `GUILD_OFFER_REGISTRY[(definition_key, issuer_branch_key)]`; keeps reward immutable and registry-owned |
| Issuer granularity | Per-character, via a new `QuestIssuer` component | Rewards differ per commissioner; a component is the project's existing "this NPC hosts service X" idiom |
| `issuer_key` source | Optional authored content key, defaulting to `#<pk>` | Authors need a key writable in import JSON (pk does not exist yet at authoring time); runtime-registered commissions need no authoring |
| Settlement | Explicit `settlement` field on the issuance | `counter` for guild, `auto` for world; an explicit field costs nothing and keeps the option open |
| Auto-settlement mechanism | Shared plan function applied in-transaction on all three quest-log write paths | The completion-observer seam is documented as scheduling-only with swallowed exceptions — unusable for payment |
| Delivery | New `DELIVER` objective + new `explore.deliver` action | The only existing player→NPC item path is the LLM `take_item` intent; offline playability is a hard invariant |
| Lore reveal sources | Three deterministic sources added | `record_lore_reveal` is currently only reachable through the LLM `reveal_lore` intent, so the codex would be permanently empty offline |
| Quest drawer structure | Split into `QuestLog.vue` (host-free) + `GuildCounter.vue` (host-gated) | Component boundary coincides exactly with the data-source boundary |
| Codex payload | Full listing plus cards in one panel | All eight registries total a few dozen short entries — far under the 65 536-byte envelope; no on-demand action needed |

## 3. Architecture

```
world/quests/         definitions · records · progress · COMPLETED transition
                      (already guild-agnostic; gains DELIVER and issuer_key)
      ↑
issuer layer (new)    who issued it · what it pays · how it settles
   ├─ guild issuance   settlement = counter  → turn_in_quest at a local GuildStaff
   └─ npc   issuance   settlement = auto     → settled inside the completing transaction
      ↑
read models           quest_log  (new, host-free)  — the player's own quest book
                      lore_codex (new, host-free)  — discovered world knowledge
                      services.guild (existing)    — what this counter can do right now
      ↑
client                QuestLog.vue + GuildCounter.vue   → quest drawer
                      LoreCodexDrawer.vue               → codex drawer (.cmdutil trigger)
```

The governing principle is unchanged and is quoted from the engine design (§ "Guild quest
economics"):

> Guild quest economics **wrap** the deterministic quest definition rather than moving quest state
> into an NPC or command.

This change adds a second wrapper. It does not move quest state.

### 3.1 What is already guild-agnostic

`QuestRecord` carries no guild field. `QuestDefinition` carries `rank` only as a difficulty label.
`accept_quest(actor, definition_key)` needs no host. Progress already advances automatically and
converges on `fulfill_record_for()`, which transitions the record to `COMPLETED` on the final
stage: `planner.py` derives DEFEAT progress from the committed `EventLog`, `room_observation.py`
handles REACH and ESCORT, `acquire.py` handles ACQUIRE. `describe_quest_detail()` already accepts a
null offer and omits the reward section.

The guild coupling is confined to `GuildQuestOffer`, `list_guild_offers`, `accept_guild_offer`,
`abandon_guild_quest`, `turn_in_quest`, and the `services.guild` panel section.

## 4. Backend A — The Issuer Layer

### 4.1 Registry

```python
class Settlement(StrEnum):
    COUNTER = "counter"   # claimed at the issuer's counter
    AUTO    = "auto"      # settled inside the completing transaction

@dataclass(frozen=True)
class QuestIssuance:
    definition_key: str
    issuer_key: str          # "guild:<branch_key>" | "npc:<content_key>" | "npc:#<pk>"
    reward: QuestReward
    settlement: Settlement

# Holds npc-namespaced issuances only.
QUEST_ISSUANCE_REGISTRY: dict[tuple[str, str], QuestIssuance]

def resolve_issuance(definition_key: str, issuer_key: str) -> QuestIssuance | None:
    """The single normalized read seam, dispatching on the key's namespace."""
```

**Amended 2026-09-06 (proposal decomposition).** The unified thing is a *read seam*, not a merged
dict. `GUILD_OFFER_REGISTRY`, `GuildQuestOffer`, `register_guild_offer`, `get_guild_offer`, and
`list_guild_offers` are left **byte-for-byte unchanged**; `QUEST_ISSUANCE_REGISTRY` stores only
`npc:`-namespaced issuances; and `resolve_issuance()` dispatches by namespace — `guild:<branch>`
builds the normalized view from the existing offer registry, `npc:<key>` reads the new one.

The earlier "`GuildQuestOffer` becomes a view over one merged registry" formulation was rejected
after measuring its blast radius: twenty-five test modules save, clear, and restore
`GUILD_OFFER_REGISTRY` directly, and several index it expecting a `GuildQuestOffer` value. Merging
the storage would force churn through all of them for no behavioural gain. Each issuer kind keeps
exactly one writer, so the two stores cannot drift, and every consumer reads through the one seam.

Registration into `QUEST_ISSUANCE_REGISTRY` is idempotent under an existing
`(definition_key, issuer_key)` identity and rejects conflicting content before replacing — the same
semantics `register_guild_offer` already has.

**Validation:** an `npc:`-namespaced issuance must carry `reward.merit == 0`. Merit is guild
currency; a private commission never grants it.

### 4.2 The `QuestIssuer` component

Added as the fifth entry of the closed `PROFESSION_COMPONENT_TYPES` vocabulary, structurally
identical to `GuildStaff`:

```python
class QuestIssuer(Component):
    name = "quest_issuer"
    service_id = DBField(default=None)      # required: the roster-sync reuse anchor
    issuer_key = DBField(default=None)      # optional authored content key
    service_binding = DBField(default=None)
    anchor_room_id = DBField(default=None)
```

**Amended 2026-09-06 (review).** `service_id` was missing from the first draft, which called the
component "structurally identical to `GuildStaff`" while giving it three fields where `GuildStaff`
has four. `world/rules/guild_economy.py::_find_service_host` reads `component.service_id`
unconditionally on whichever class anchors a profession row, so a commissioner blueprint anchored on
a field-less class would raise `AttributeError` inside `at_server_start` and take down the whole
guild-economy sync. See §13's review findings for the full correction, including the contract test
that now pins the underlying invariant.

`issuer_key` resolution:

| Component state | Resolved issuer key | Registration timing |
|---|---|---|
| `issuer_key = "grey_granny"` | `npc:grey_granny` | Authored ahead of time, registered at startup |
| `issuer_key = None` | `npc:#<pk>` | Registered at runtime |

Both forms share one registry and one lookup rule. Runtime-registered issuances are mirrored into
`GeneratedQuestStore` alongside generated definitions, because the process-local registries are
rebuilt from that durable store on every `at_server_start`.

The component earns its place by being the **authorization** gate, not merely a key source (`pk`
would suffice for a key). Only an NPC an author gave the component to can issue commissions.

### 4.3 Record field

`QuestRecord` gains `issuer_key: str`. This is required for correctness: when one definition has
been issued both by the guild and by a shopkeeper, the record must say which issuance governs its
reward and settlement.

The field is **required**, not optional-with-default. The `tracked` precedent exists but is a
backward-compatibility mechanism, and §11 rules those out: the project has no released users and
owes no migration. The consequence is explicit — quest-log entries written before this change fail
`from_storage` and must be recreated in development databases.

### 4.4 AI boundary

`_apply_offer_quest` in `world/rules/npc_intents.py` currently rejects any speaker lacking
`GuildStaff`. The gate widens to `GuildStaff` **or** `QuestIssuer`, and verifies a registered
issuance at that speaker's resolved `issuer_key`. This is not a loosening: the AI still cannot
choose the issuer identity, invent an issuance, or make an unauthorized NPC issue anything. Guild
issuances additionally keep the existing registration and rank-band checks.

## 5. Backend B — Delivery

### 5.1 The gap

The registered exploration actions are `move`, `look`, `talk_scripted`, `talk_freeform`,
`dialogue_leave`, `party_invite`, `party_leave`, `engage`, `wait`, `possess`, `possess_release`.
There is no give verb and no `給` command. The only path moving an item from player to NPC is the
LLM `take_item` intent. A delivery quest built on that path deadlocks when the LLM is offline,
violating the project's headline invariant that the deterministic game stays fully playable with
every generative service down.

### 5.2 Design

`ObjectiveKind.DELIVER` carries `item_key`, `quantity`, and a recipient bound through the existing
`objective_target_ids` runtime binding.

A new deterministic action `explore.deliver` (with its player command) hands bound quest items to a
co-located recipient, reusing the existing `_transfer_items()` primitive, which already snapshots
both parties' inventory, quest log, and traits and restores everything on failure. DELIVER progress
advances from the committed removal when the receiver matches the record's bound recipient —
mirroring how ACQUIRE advances only from a committed positive inventory delta.

This also supplies the `給` verb the redesign document already anticipated for the exploration
surface.

**Documentation obligation:** the change adds a player command, so `docs/game/commands.md` and
`docs/game/command-reference.md` are updated in the same change and `tests/test_command_docs.py`
stays green.

## 6. Backend C — Automatic Settlement

### 6.1 Why not the completion observer

`register_quest_completion_observer` is documented as a scheduling seam: observers must defer side
effects through `transaction.on_commit`, and an exception one raises is isolated and logged so that
"a broken observer can never change quest settlement". Paying a reward there would pay after commit
and swallow failures silently. Title nomination belongs on that seam; money does not.

### 6.2 Design

A pure function `plan_auto_settlement(actor, completed_records)` computes the wallet and inventory
plan for every record that just reached `COMPLETED` under an `AUTO` issuance. The three quest-log
write paths each commit it inside their own transaction:

| Write path | Used by | Commit mechanism |
|---|---|---|
| `apply_quest_log_replacement` | REACH/ESCORT observation, deadline settlement, binding, accept, track | Inside its existing `transaction.atomic()` |
| `apply_quest_log_delta` | Inventory plans, reward settlement, shop operations | Inside the caller's transaction |
| `pending_effects_for_transition` | DEFEAT (committed by `ActionResolver`) | Additional `PendingEffect` values |

Settlement writes the quest ID into `guild_reward_claims`, so automatic and counter settlement
share one de-duplication ledger and a quest can never be paid twice.

## 7. Backend D — Deterministic Lore Reveals

`record_lore_reveal()` has exactly one caller today: the LLM `reveal_lore` intent. Three
deterministic sources are added, all reachable offline, all routed through that same sole writer so
the append-only semantics are unchanged:

| Trigger | Reveals | Hook site |
|---|---|---|
| Entering an anchor or wilderness region | the matching `anchor` / `region` entry | the room-entry observation point in `world/quests/room_observation.py` |
| First defeat of a monster tier | the matching `monster` entry | the `target_defeated` event the DEFEAT planner already reads |
| Character creation and guild registration | the chosen `race` / `nation`, and the `guild` rank entry | the creation and registration commit paths |

## 8. Read Models

### 8.1 `quest_log` v1 (host-independent)

One row per stored record, in quest-log order, capped at `MAX_QUEST_ROWS` (12):

```
quest_id, definition_key, display_name, state,
stage_index, stage_total, stage_progress, objective_quantity,
objective_line, deadline_line, detail, tracked,
issuer:     { kind, key, label },   # kind: guild | npc; label is the display name
settlement,                          # counter | auto
reward_line,                         # nullable
track:      <action descriptor>      # guild.quest_track, always enabled
```

All prose comes from the canonical `describe_objective` / `describe_deadline` /
`describe_quest_detail` / `describe_reward` seams, so the quest book, the objective tracker, and the
guild counter can never disagree. A `QuestDataError` from the strict reader degrades the whole panel
to the registry-owned common unavailable form — never a partial row list.

The existing `objectives` panel is **unchanged**. It serves the HUD tracker island with different
bounds (three tracked, in-progress rows) and a different lifecycle. Both derive from the same
describe seams, so the duplication cannot drift.

### 8.2 `lore_codex` v1 (host-independent)

Discovered entries grouped by the eight `CODE_CATEGORIES` in mapping order, each with its rendered
card fields. The full payload is carried in one panel: the eight registries hold a few dozen short
entries in total, far under the 65 536-byte envelope, and the registries are immutable module-level
data that generation never extends. The presenter still enforces explicit row and per-field bounds
and fails closed on the envelope check, so registry growth surfaces as a loud test failure rather
than a truncated payload. The client performs the two-level navigation locally; no OOB
action and no on-demand fetch is needed.

Undiscovered entries do not appear at all, and category counts count only discovered entries — the
same non-disclosure rule `commands/lore.py` enforces by returning one fixed not-found line for
unknown categories, unknown keys, and undiscovered entries alike.

## 9. Client

### 9.1 Quest drawer

`QuestBoard.vue` (496 lines, two data sources after this change) is replaced by two components
hosted in the same drawer:

```
┌─ 任務 ─────────────────────┐
│ 我的任務簿                  │  QuestLog.vue     ← quest_log panel, always present
│  ▸ 討伐低階魔物      公會    │
│  ▸ 送藥至北岸      灰婆婆    │
├───────────────────────────┤
│ 公會櫃台【僅職員面前】        │  GuildCounter.vue ← services.guild, host-gated
│  註冊 · 任務板 · 等級考核     │
└───────────────────────────┘
```

**`QuestLog.vue`** lists every accepted quest, labelled by issuer. Per-row actions:

- Track / untrack: always available (`guild.quest_track` is already host-independent by contract).
- Abandon / turn in: rendered only when `services.guild.quests` carries a row with the same
  `quest_id` and that action is enabled. Matching by `quest_id` is the single merge point between
  the two panels.

**`GuildCounter.vue`** owns only what belongs to the counter itself: registration, the quest board
(accepting new quests), and guild rank with the promotion examination. It does not re-list accepted
quests, so nothing is shown twice.

This matches the stated rule exactly: only accepting new quests, browsing the board, turning quests
in, claiming rewards, and taking the rank examination require standing before a clerk.

### 9.2 Codex drawer

`LoreCodexDrawer.vue` replaces `LoreDrawer.vue`. The old component's guild quest prose is pure
duplication once `QuestLog.vue` exists, and is removed with it.

The layout follows the redesign mockup (`docs/design/elosern-redesign/index.html`, the `dr-lore`
aside): header `圖鑑 · 僅已發現 · 8 類`, a category pill row with per-category counts, an entry
list, and an entry card — two levels of navigation. The mockup's placeholder category names are
superseded by the eight implemented categories (種族 / 國家 / 地域 / 魔物 / 元素 / 魔法 / 地點 /
公會).

### 9.3 Command-line utility strip

The `世界圖鑑` button is removed from `QuestBoard.vue` and becomes a fifth `.cmdutil` icon:

```
┌─ .cmdutil ─────────────────────┐
│  技能系譜  圖鑑  稱號冊  設定  說明  │
└────────────────────────────────┘
```

The four existing icons open overlays; this one opens a drawer, which the store's `openHudDrawer`
already supports. The title codex (`title_codex`, epithets) and the world codex (`lore_knowledge`,
world knowledge) are separate systems and are placed side by side, so their glyphs must be clearly
distinguishable.

## 10. Contracts and Specifications

**OpenSpec capabilities affected:** `quest-lifecycle`, `quest-progress-tracking`,
`quest-reward-settlement`, `guild-quest-board`, `dialogue-offer-quest`, `lore-knowledge`,
`webclient-service-menus`, `game-command-docs`.

**New capabilities:** `quest-issuance`, `quest-delivery`, `webclient-quest-log-panel`,
`webclient-lore-codex-panel`.

**Other obligations:**

- New DOM test identifiers are registered in
  `docs/development/webclient-vue-frozen-contract-audit.md` §2.3.
- Both new panels get a JS validator mirroring the Python bounds, covered by the existing
  dual-direction parity test.
- Every new persistent state change, boundary, and cross-system workflow emits its facade event per
  the observability catalog, and the observability lint runs with the focused tests.

## 11. Out of Scope (YAGNI)

- No data migration or backward-compatibility layer: the project has no released users.
- Rewards stay in the immutable registry and never move into `QuestRecord`, where they would become
  mutable player state and an economy hole.
- The `objectives` panel schema is untouched.
- No "return to the commissioner to claim" flow for world quests — `npc:` issuances are always
  `AUTO`. The `settlement` field is already there if that changes.

## 12. Implementation Phases

Each phase stands on its own tests.

1. **Issuer layer** — registry, `QuestIssuer` component, `QuestRecord.issuer_key`, validation,
   `GuildQuestOffer` as a guild-namespaced view.
2. **Automatic settlement** — `plan_auto_settlement` plus the three write paths and claim
   de-duplication.
3. **Delivery** — `DELIVER` objective, `explore.deliver` action and command, command documentation.
4. **Deterministic lore reveals** — the three sources.
5. **Read models** — `quest_log` and `lore_codex` panels with JS validator parity.
6. **Client** — `QuestLog.vue`, `GuildCounter.vue`, `LoreCodexDrawer.vue`, the `.cmdutil` icon, and
   removal of `QuestBoard.vue` / `LoreDrawer.vue`.
7. **Generative pipeline** — `compile.py` emitting `npc:` issuances, and the widened `offer_quest`
   intent gate.

## 13. OpenSpec Change Decomposition

**Added 2026-09-06; revised after review.** The seven phases above decompose into thirteen OpenSpec
changes, each sized to one engineer-workday. Phases 1, 3, 5, 6, and 7 each split, because each
combined more work than a single day holds.

| # | Change | Owns | Depends on |
|---|---|---|---|
| 1 | `quest-issuance-registry` | Issuer-key grammar, `Settlement`, `QuestIssuance`, the private-commission registry, the `resolve_issuance` seam, the merit-free rule | — |
| 2 | `quest-record-issuer-key` | `QuestRecord.issuer_key` (required), `accept_quest`'s issuer argument and resolve-before-create rule, the guild acceptance path | 1 |
| 3 | `quest-issuer-component` | `QuestIssuer` component, vocabulary and rulebook entry, the row-anchor contract test, `resolve_issuer_key`, import authoring | 1 |
| 4 | `quest-auto-settlement` | `plan_auto_settlement`, the three write paths, the shared claim ledger | 1, 2 |
| 5 | `quest-deliver-objective` | `ObjectiveKind.DELIVER`, its validation and prose, the delivery observer, the transfer hook | — |
| 6 | `quest-deliver-action` | `explore.deliver`, the player command, the exploration affordance, command docs | 5 |
| 7 | `lore-deterministic-reveals` | Arrival, first-defeat, and origin reveal sources; the non-blocking rule | — |
| 8 | `webclient-quest-log-panel` | The `quest_log` read model, its bounds, push timing, and JS mirror | 1, 2 |
| 9 | `webclient-lore-codex-panel` | The `lore_codex` read model, its bounds, push timing, and JS mirror | — |
| 10 | `webclient-lore-codex-drawer` | `LoreCodexDrawer.vue`, the `.cmdutil` icon, deletion of `LoreDrawer.vue` | 9 |
| 11 | `webclient-quest-drawer-split` | `QuestLog.vue`, `GuildCounter.vue`, deletion of `QuestBoard.vue` | 8, 10 |
| 12 | `quest-issuance-generative` | `compile.py` issuances, the durable store payload and restore path | 1, 2, 3 |
| 13 | `quest-issuance-dialogue-gate` | The widened `offer_quest` speaker gate and per-kind eligibility | 1, 2, 3 |

Change 13 was split out of 12 during review. Widening an AI-reachable boundary is the
highest-risk edit in the feature and deserves its own reviewable unit rather than sitting inside a
`CompiledQuest`-plus-durable-store refactor; the combined change also exceeded one workday. The two
are siblings, not sequential — 13 verifies whatever issuances exist, however they were registered.

### Code conflicts

Only two pairs touch the same files:

- **10 and 11** both edit `web/webclient-app/AppClient.vue` and
  `docs/development/webclient-vue-frozen-contract-audit.md` §2.3. Change 10 also edits
  `QuestBoard.vue`, which change 11 deletes. **Land 10 before 11** — the button removal is then a
  two-line edit rather than a conflict against a deleted file.
- **8 and 9** both edit `web/webclient/presentation/registry.py`,
  `web/static/webclient/js/elosern/protocol.js`, and `.github/evennia-shards.json`. They land in
  different batches, so they never run concurrently; if they are reordered, run them sequentially.

Everything else is file-disjoint. Notably 2 and 3 both depend on 1 but touch nothing in common
(`world/quests/runtime.py` and the guild acceptance path versus `typeclasses/components.py` and the
profession registries). Changes 12 and 13 were one change until review; splitting them also split
their files — 12 owns `world/quests/compile.py` and the durable store, 13 owns
`world/rules/npc_intents.py` — so they are disjoint and may run in parallel.

Change 2 also edits `world/rules/npc_intents.py` (task 2.3: the `offer_quest` applier passes the
guild-derived key), which 13 later widens. They land in different batches, so they never run
concurrently.

### Advised parallel batch order

| Batch | Changes | Rationale |
|---|---|---|
| **A** | 1, 5, 7, 9 | No dependencies and fully file-disjoint. Lands the issuance model, the delivery objective, the codex's data source, and the codex read model in parallel. |
| **B** | 2, 3, 6, 10 | Each unblocked by exactly one batch-A change. Disjoint: quest runtime, components, the delivery player surface, the codex client surface. |
| **C** | 4, 8, 12, 13 | Each needs 1 and 2 plus, for 12 and 13, change 3. Disjoint: settlement in `world/quests/transitions.py`, the quest read model, the compile pipeline, the dialogue gate. |
| **D** | 11 | Needs both 8 and 10; conflicts with 10 on `AppClient.vue`, so it lands last and alone. |

Three ordering constraints override any reshuffling: **2 before 4, 8, 12, and 13** (all four read
`QuestRecord.issuer_key` or call `accept_quest` with an issuer argument), **3 before 12 and 13**
(both verify an authorized carrier), and **10 before 11** (the `AppClient.vue` and audit-document
conflict).

### Breaking changes to development data

Two changes invalidate existing development state. Neither writes a migration; the project has no
released users.

- **2** makes `issuer_key` a required record field, so quest-log entries written before it fail the
  strict reader. Development quest logs must be recreated.
- **12** changes the `GeneratedQuestStore` payload shape. The store must be cleared.

### Deliberate interim states

- After **1**, the issuance registry has no consumer. This is a forward-declared seam, which
  `AGENTS.md` explicitly sanctions; its delta spec's scenarios are the guard.
- After **5** and before **6**, `DELIVER` advances only through the LLM-driven transfer. No content
  should author a delivery quest until **6** lands.
- After **10** and before **7**, the codex drawer renders an honest empty state offline. That is
  correct behavior for an empty codex; **7** fixes the cause.

### Review findings folded in

A rubber-duck review of the decomposition found one blocking defect and two gaps, all corrected
above and in the affected changes.

**Blocking — `QuestIssuer` would have crashed startup synchronization.** §4.2 originally gave the
component three fields and called it "structurally identical to `GuildStaff`". It is not:
`GuildStaff`, `GuildExaminer`, and `Merchant` all also carry `service_id`, and
`world/rules/guild_economy.py::_find_service_host` reads `component.service_id` **unconditionally**
on whichever class anchors a profession row (`_row_anchor_class` takes `row.profession.components[0]`).
A commissioner blueprint anchored on a field-less `QuestIssuer` would raise `AttributeError` inside
`at_server_start`, taking down the entire guild-economy sync on every restart — not just quest
issuance.

The component now carries `service_id`, making the "identical to `GuildStaff`" claim actually true.
The underlying invariant — every profession row's first component must define `service_id` — holds
today only by convention (`ScriptedDialogue` also lacks it and simply never appears first), so
change 3 additionally lands a contract test stating it, and roster-sync tests that run the sync
twice with a commissioner row present.

Relatedly, `issuer_key` deliberately does **not** join `_IDENTITY_KWARGS`. That set is the
required-identity contract and `missing_identity_kwargs` rejects a blank value, whereas an absent
`issuer_key` is the valid identity form. The accepted consequence is that `project_row_kwargs` never
projects an authored key onto a roster-created commissioner, which resolves to `npc:#<pk>`; authored
content keys arrive through the import path, whose `resolve_component_plan` passes kwargs verbatim.

**Missing dependency.** Change 12's declared dependencies omitted change 2, even though it calls
`accept_quest` with an issuer argument. The batch table already sequenced it correctly, but the
override-constraints list did not, so a reader following the constraints rather than the batches
could have concluded 12 was safe before 2. Corrected in both places.

**Spec completeness.** `quest-deliver-action` modified the affordance vocabulary requirement to admit
`explore.deliver` into `ACTION_CODE_ALLOWLIST`, but left the sibling requirement "Affordance params
are validator-normalized" untouched — and that requirement's text claims to enumerate the exact
params shape of every allowlisted action. Archiving would have produced an internally inconsistent
main spec. That requirement now carries a MODIFIED delta naming the delivery payload shape.
