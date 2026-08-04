## Context

The deterministic guild economy (change 16), quest lifecycle (change 15), persistent combat sessions, and the `webclient-oob-foundation` (23a) are all live. The combat-menu change (23b) established the template this unit follows: a read-only versioned panel (`context_actions`) built by a no-mutation view (`world/rules/combat_view.py`), a set of exact allowlisted action adapters (`web/webclient/actions/combat_actions.py`), a DOM-independent menu module (`elosern/combat_menu.js`) plus a GoldenLayout dock plugin (`plugins/combat_dock.js`), and Node/browser/Evennia gates that reuse the locked Playwright harness. The `map-knowledge-minimap` change (23c) added the `local_map` panel with shared Python/JavaScript bounds and a serialized-size envelope test.

This design implements the approved `webclient-service-menus` delivery unit (roadmap item 23e) from
`docs/superpowers/specs/2026-08-02-webclient-ui-design.md` (§7.5) and
`docs/superpowers/specs/2026-08-02-webclient-service-creation-ui-design.md`. That focused design covers two delivery units; **this change owns the service menus only** — character creation (23g) is explicitly out of scope. Service menus run in exploration mode and depend on the same foundation form, focus, revision, and dispatcher rules as every other panel. The browser stays a read-only renderer, Telnet play is unchanged, and the single-writer rule is preserved: this change adds no deterministic mutation API; it calls only public APIs already owned by `world/rules/`.

The existing deterministic entry points this unit consumes are all public and side-effect-isolated:
`register_adventurer`, `resolve_local_service_host`, `list_guild_offers`, `accept_guild_offer`,
`abandon_guild_quest`, `turn_in_quest`, `start_guild_exam`, `economy.buy`/`economy.sell`,
`shop_is_open`, `parse_merchant_stock`, `read_records`/`find_record`, `world.quests.describe`,
`world.skills.equipment.list_items`, the `guild_config` catalog, and the immutable lore registries.
The adapter dispatcher contract in `webclient-action-dispatch` currently fixes the production registry
at exactly the three combat actions; this change amends that contract.

## Goals / Non-Goals

**Goals:**

- Present guild registration, board, quest log, rank/examination, shop stock/quantity, buy/sell, and
  repeated-key inventory through bounded, keyboard-first panels in exploration mode.
- Register exactly seven allowlisted service adapters that re-resolve the local host and every
  referenced identity and call only existing deterministic APIs.
- Keep presentation and dispatch read-only relative to canonical state: a new no-mutation service read
  model in `world/rules/` builds the panel; adapters never assign `.db`, traits, registration, quests,
  wallet, inventory, stock, merit, or rank.
- Preserve every deterministic guarantee — local-only hosts, exactly-once reward claims, exact integer
  copper, stock caps, ACQUIRE progress, and all-or-nothing activation/exam transitions — as server
  checks repeated at commit.
- Reuse the foundation epoch/revision/in-flight/dispatcher semantics and the `context_actions` combat
  hand-off so `guild.exam_start` moves the shell into the ordinary combat menu.
- Extend the Node, Evennia, and managed Playwright gates with independent guild/quest/shop/inventory
  journeys.

**Non-Goals:**

- No character-creation UI (23g), exploration root/movement/look/interaction/dialogue/rest-wait (23d),
  art, or combat-menu changes.
- No new quest, guild, shop, item-use, equipment-effect, or character-build mechanics.
- No client-side price, reward, rank, merit, stock, or trait-allocation authority; no client-side clock.
- No remote or ambiguous host addressing; no host/branch/dbref/actor/session/price/stock fields in any
  action payload.
- No generic `guild.command` or `shop.command`; no action routed through the text command parser.
- No mobile acceptance, no new runtime dependency, no database migration, no backward-compatibility
  layer, no Telnet behavior change.
- No use/consume/equip controls in inventory — those wait for an owning deterministic API and
  requirement.

## Decisions

### D1. One `services` panel with three nullable surfaces instead of per-service panels

The production presentation registry registers a single `services` panel (schema version 1) available
in exploration mode. Its available payload carries a display-only `host`, a `player` summary, and three
bounded nullable sections — `guild`, `shop`, and `inventory`. In combat or creation mode, and when a
global prerequisite (actor or player summary) cannot be read without mutation, the whole panel uses the
common unavailable form; a failure confined to one surface degrades only that surface.

**Host resolution is per service class, not one shared rule.** Each surface independently resolves its
own host from the actor's current room with `resolve_local_service_host(actor, <component_class>)`:
`guild` and `rank` resolve `GuildStaff` and `GuildExaminer`, and `shop` resolves `Merchant`. Zero or
multiple hosts of the class a surface requires make that surface unavailable. Different host classes in
one room are not cross-class ambiguity — a hall whose `GuildStaff` host also carries `GuildExaminer`
yields both the guild and rank surfaces, and a room with both a staff host and a merchant yields both
guild and shop. The top-level `host` is display-only reconciliation metadata (the resolved single local
`GuildStaff` else `Merchant`, else null) and is never an availability authority and never submitted in
an action payload; the adapters re-resolve the authoritative host class per action (D3).

Separate panels per service (`guild_panel`, `shop_panel`, `inventory_panel`) were rejected: services
all run in the same mode and the focused design's "Shared Service Panel Contract" (§3) describes one
payload contract with a service kind. A single panel also keeps the `webclient-action-dispatch` and
panel-allowlist deltas small and lets one presenter isolate surfaces independently (D2). The Altoria
layout puts the guild hall and general store in separate rooms, so in practice exactly one host-driven
surface is non-null per room; `inventory` is always non-null in exploration mode because it is a
personal surface with no host requirement.

### D2. A frozen no-mutation service read model isolates each surface

`world/rules/service_view.py` builds a JSON-safe, bounded view from canonical state — guild
registration, quest log, catalog offers, merchant stock, wallet, inventory, rank/merit — through the
existing strict parsers (`parse_guild_registration`, `read_records`, `parse_merchant_stock`,
`list_guild_offers`), reusing `world.quests.describe` for objective summaries, reward summaries, and
full quest detail, and `get_catalog()`/`shop_is_open()` for shop and threshold data. It performs no
writes, never constructs a lazy handler that materializes defaults, never creates a clock (it reads the
same read-only `get_world_clock()` accessor the status panel uses), and never reads `disguised_stats`.

Each surface degrades independently: a corrupt quest log or malformed merchant stock marks only that
section's data as unavailable while the remaining sections and narrative stay healthy. The whole-panel
unavailable form is reserved for global prerequisites — the puppet is not in exploration mode or the
actor/player summary cannot be read without mutation. This mirrors presenter isolation at a sub-panel
level and follows the `combat_view.py` / `status_query.py` precedent of keeping presenters thin and
deterministic builders in `world/rules/`. The presenter
(`web/webclient/presentation/services.py`) validates its own output against the exact bounded schema
before returning it, exactly as `combat_panel.py` does.

### D3. Adapters re-resolve the local host and every identity; payloads carry no authority

Each service adapter receives only the session puppet. `guild.*` adapters resolve the local
`GuildStaff` host with `resolve_local_service_host(actor, GuildStaff)`; `guild.exam_start` resolves
`GuildExaminer`; `shop.*` resolve `Merchant`. Referenced `quest_id`, `definition_key`, `item_key`, and
`target_rank` values are re-read against current canonical state inside the adapter before the domain
API is called. `guild.exam_start` re-derives the exact next rank from `actor.guild_rank` and rejects
any other `target_rank`.

Accepting a host dbref/identity from the client was rejected because the commands themselves reject
remote interaction and the focused design forbids the browser selecting a global merchant or examiner.
This is the same reasoning the combat adapters apply to session participants. The payload schemas are
therefore exactly the fields in the focused design's §6 action table plus the bounded quantity for
`shop.buy`/`shop.sell`; no actor, host, branch, session, price, stock, or wallet field exists.
`guild.register` is deliberately idempotent: the deterministic `register_adventurer` already returns the
canonical record for an already-registered actor, so the adapter reports success and refreshes the
panels rather than inventing a rejection that the domain API does not produce; the panel only surfaces a
register action to unregistered players, but a stale or replayed registration is a safe no-op refresh.

### D4. Exact bounded payload schemas shared between Python and JavaScript validators

Following `local_map`'s D10a pattern, the `services` schema constants live in the presenter and are
mirrored in `elosern/protocol.js`, guarded by a dual-direction parity test. Bounds stay below the OOB
globals and are sized so a simultaneous-max payload still fits the 65,536-byte envelope with headroom:
at most 12 board rows, 12 quest rows, 12 stock rows, 12 sellable rows, and 32 inventory rows; keys and
quest IDs 1..64, display names 1..128, summaries and reward lines 1..128, quest detail 1..512,
deadline lines 1..64, rank keys 1..8, host display names 1..256; action IDs 1..64, labels 1..64,
disabled-reason messages 1..128; quantities are integers in 1..1000. The panel additionally carries a
small exact `pagination` object (one non-negative integer per surface, capped at that surface's row
ceiling) that reports shipped row counts, satisfying the focused design's "pagination metadata for
bounded lists" shared-contract item without in-band paging or a fetch mechanism. A worst-case budget
estimate
(12 board rows ≈ 8.4 KiB, 12 quest rows including 512-char detail ≈ 14 KiB, 12 stock rows ≈ 7 KiB,
12 sellable rows ≈ 6.7 KiB, 32 inventory rows ≈ 6.6 KiB, plus fixed summary/JSON overhead ≈ 4 KiB)
keeps the structurally maximal realistic payload comfortably under 48 KiB.

The envelope guarantee is enforced on **serialized size**, not just per-field bounds: both validators
compute the canonical UTF-8 byte length of the assembled payload and fail closed when it exceeds the
65,536-byte OOB envelope limit, exactly as `local_map` does. Per-field ceilings are independent
safety limits; conformance is defined and enforced by the byte budget, so a payload that simultaneously
maximizes every string field is rejected by the byte gate rather than accepted per-field. A worst-case
serialization test proves the structurally maximal realistic payload fits, and a second test proves an
all-ceilings payload is rejected — both mirrored in Node.

### D5. Action descriptors advertise enabled state, disabled reason, and quantity bounds as previews only

Every row carries an `action` descriptor (`action_id`, `label`, `enabled`, `disabled_reason`, and a
nullable `quantity` bounds object used by `shop.buy`/`shop.sell`). Disabled reasons are derived from
deterministic state (closed shop, unregistered, insufficient funds, insufficient stock, stock cap,
ineligible rank, already claimed) and are always rechecked at commit. `buy`/`sell` descriptors advertise
a server-computed quantity maximum (live stock for buy; for sell the held count additionally capped by
the merchant's remaining stock capacity, and both capped at 1000) so the browser never offers a
guaranteed-fail quantity while the deterministic API keeps its own cap check for stale/tampered
payloads. The browser renders the server-provided unit price and an explicitly non-authoritative
running total; the submitted payload carries only `item_key` and `quantity`, and the committed copper
total arrives in the action result. No client value can authorize a different price, stock, or reward.

**Staleness is the existing dispatcher contract, not a per-row comparison.** Service actions carry the
same `presentation_epoch`/`base_revision` envelope as every other action; a mismatch is the dispatcher's
`stale` outcome plus a full snapshot, defined once in `webclient-action-dispatch` and not re-specified
here. A price, stock, or rank that changes between render and commit is **not** a stale condition — the
deterministic API rechecks current canonical state at commit and the returned snapshot shows the
committed result, matching the focused design's "domain state at commit is authoritative". This avoids
an impossible requirement: with only `{item_key, quantity}` on the wire, the server cannot know what
price a stale client was shown, so it must never claim a per-row price diff is staleness.

### D6. A keyboard service dock and DOM-independent menu model

The action dock gains a Services root entry rendered by a `services_dock.js` GoldenLayout plugin in
exploration mode. A DOM-independent `elosern/service_menu.js` module owns the menu state: which surface
is open (Guild, Shop, Inventory), which submenu (Board / Quests / Rank / Stock / Sell / Items), row
focus within the bounded lists, the quantity form state, and the destructive-abandon confirmation
screen. Arrow
keys navigate, Enter opens/submits, Space reserves multi-select for future use, and Escape pops one
level. Disabled rows remain focusable so their reason is readable but submit nothing. The quantity form
uses Tab/Shift+Tab for the field and rejects empty, non-integer, boolean-like, negative, zero, or
oversized values before sending; the server repeats positive-quantity, funds, stock, price, and cap
checks. The dock locks while a mutation is in flight and until the declared presentation revision is
accepted, exactly as the combat dock does. `guild.exam_start` needs no confirmation (only Abandon is
destructive per the focused design §8), but its mode transition to the combat dock is rendered from the
mode-changing update. **Mode ownership is exclusive:** when the client atomically adopts a valid update
or snapshot whose mode is `combat`, the service dock synchronously unloads, unregisters its keyboard
handlers, discards local quantity/selection/confirmation state, and only the combat dock owns
action-dock focus; when a later settlement returns the actor to exploration mode, the service dock
remounts from the canonical snapshot. This reuses the client's atomic panel-plus-mode replacement
rather than adding a second teardown mechanism.

### D7. Mode transition and affected-panel publication for `guild.exam_start`

The existing dispatcher already mandates publication before result and declares nonempty affected-panel
sets. Service adapters declare: `guild.register` → `status`+`services`; `guild.quest_turnin`,
`shop.buy`, `shop.sell` → `status`+`services`; `guild.quest_accept`/`guild.quest_abandon` →
`services`; `guild.exam_start` → `status`+`services`+`context_actions` with the new `combat` mode in
the update envelope. Because mode is part of the update metadata and `context_actions` already switches
to its combat form when a session exists, the existing protocol handles the hand-off with no new
mechanism and **no full snapshot is required** — the single `ui_update` atomically replaces mode, the
combat panel, and the (now-unavailable) services panel at one revision; the `services` presenter simply
returns its unavailable form in combat mode.

### D8. Reuse the deterministic detail renderer instead of re-implementing prose

Quest rows carry a server-rendered `detail` string produced by `world.quests.describe.describe_quest_detail`
with the current world tick injected. The browser opens a detail pane by rendering that string as text
and never reconstructs objective or reward prose in JavaScript. This satisfies the focused design's
"opens the current quest detail renderer rather than reconstructing prose in JavaScript" with zero new
rendering surface and keeps the payload deterministic and testable.

### D9. Stable rejection codes and Traditional Chinese messages live in one mapping

`world/rules/service_messages.py` maps every deterministic service rejection — `RegistrationReason`,
`BoardAccessError`/`GuildOfferError` states, `RewardClaimError`, `ExamReason`, `TradeReason`, and
`GuildDataError`/`QuestDataError`/`QuestNotFound` — to a stable `code` (the enum value or a derived
identifier) and a safe Traditional Chinese message mirroring the command output. Adapters use this
mapping so the browser and Telnet present identical reasons. An unknown/unmapped exception falls back to
a generic `service_rejected` code with the safe message and never exposes a traceback or raw payload.

### D10. The change touches no deterministic domain API

No rule, quest, shop, guild, or inventory behavior changes; `webclient-action-dispatch` is the only
spec-level contract amended, and only `registry.py`/`protocol.js` allowlists and the action-dock
surface change in landed code. This keeps the single-writer boundary intact and lets the change be
reviewed entirely at the presentation/adaptation layer.

## Risks / Trade-offs

- [The composite panel can grow past the envelope budget] → Ceilings are sized so a simultaneous-max payload stays under 48 KiB (D4), a worst-case serialization test proves the structurally maximal realistic payload fits, and an all-ceilings payload is rejected by the byte gate; both mirrored in Node.
- [A corrupt quest log or malformed stock could break the whole panel] → The read model isolates each surface (D2); a corrupt personal record degrades only that section while status, narrative, and other surfaces stay healthy, and the whole-panel unavailable form is reserved for global prerequisites.
- [The browser could submit a price, stock, or reward it was shown] → Descriptors are previews only; adapters re-resolve hosts and identities and call the deterministic APIs, which recheck open state, quantity, funds, stock, cap, rank, and exactly-once claims (D3, D5).
- [A stale client could be shown a price that changed at commit] → Staleness is exactly the existing epoch/revision dispatcher outcome; a commit-time price/stock diff is resolved against current canonical state and shown in the returned snapshot, never claimed as stale (D5).
- [A mode change could desync or double-render the dock] → The client atomically adopts mode+panels at one revision; the service dock unloads synchronously and only the active mode's dock owns action-dock focus (D6, D7).
- [Quest detail could drift from the quest runtime] → The panel renders the same `describe_quest_detail` the `guild show` command uses, keeping one source of prose (D8).
- [Exploration dock overlap with 23d] → 23e ships a Services root and panel payloads; 23d's later delta re-homes them under its Interact/Quests/Inventory entries and will amend the same shell surface. The panel and adapter contracts are the stable seam both share.
- [An unmapped rejection could leak internals] → Every deterministic reason is mapped to a stable code and Traditional Chinese message; an unmapped exception degrades to a generic safe message with no traceback (D9).
- [Stale or duplicate service mutations could double-apply] → The foundation's revision/request-ID/in-flight checks and the dispatch "publish before result, unlock after declared revision" rule are reused unchanged; adapters declare no mutation until domain revalidation passes (D6).

## Migration Plan

No stored schema changes and no data migration: the project is unreleased with zero users, the new panel
and adapters are additive, and only the production registry's allowed action set grows. Implement in
dependency order: service read model and messages → presenter + schema → action adapters and registry →
client protocol allowlist + `service_menu.js` → `services_dock.js` → Node and Evennia gates → managed
Playwright journeys → spec sync, traceability, and coverage. Rollback is the ordinary code-revision
rollback; no dual reader or data restore is needed because the change adds no new persistent field and
never weakens an existing deterministic check.

## Open Questions

None. The observable scope — one read-only `services` panel with per-class host resolution, seven
allowlisted service adapters, a no-mutation read model, a keyboard service dock with bounded quantity
forms and an abandon confirmation, exam-to-combat mode transition with exclusive dock ownership, and
independent guild/quest/shop/inventory acceptance — is fixed by the approved parent and focused
designs. The only contract amended is `webclient-action-dispatch`, and the
exploration-dock surface shared with 23d remains an explicitly sequenced hand-off.
