# title-system Specification

## Purpose

Define deterministic title storage, the fixed-title lore registry, transactional title grants, the swap-only equip surface, and the narrative consumers that compose the player-facing full title (稱號　異名).

## Requirements


### Requirement: Title state is a two-kind collection and a two-slot equip record
`db.title_collection` SHALL be a list of entries identified by `(kind, key |
display)`: fixed entries `{"kind": "fixed", "key", "granted_tick"}` and epithet
entries `{"kind": "epithet", "display", "origin_quote", "granted_tick"}`. Fixed
keys SHALL appear at most once (duplicate grants are silent no-ops); epithet
displays SHALL be unique within the collection; fixed entries SHALL never be
removable (no delete API, command, or code path — asserted by a structural test).
`db.title_equipped` SHALL be `{"fixed": <fixed key or None>, "epithet": <display
or None>}`, storing identifiers (never copies). Both attributes SHALL be
registered on the snapshot/restore surface before any writer; missing attributes
SHALL read exactly as `[]` and `{"fixed": None, "epithet": None}`. Bank writers
SHALL validate every input before any write — a fixed key must name a registry
row, epithet display and origin quote must be non-blank strings, the epithet
display must fit its storage cap, and `granted_tick` must be a non-negative
integer — and SHALL raise `TitleDataError` leaving state byte-identical.

#### Scenario: Duplicate fixed grant is a no-op
- **WHEN** an entity already holding fixed key `g_f_rank` is granted it again
- **THEN** the collection and equip record are byte-identical to before

#### Scenario: Rolled-back grants restore both attributes
- **WHEN** a triggering action commits a title write and a later failure restores the action snapshot
- **THEN** `title_collection` and `title_equipped` return to their pre-action values

### Requirement: compose_title is the single pure composition of the full title
`world/rules/titles.py` SHALL define
`compose_title(fixed: str | None, epithet: str | None) -> str` joining the
non-empty parts fixed-first, epithet-second, with a full-width space (「　」),
returning the empty string when both slots are empty. No consumer SHALL store a
composed copy; every read composes live from the two slots' identifiers. On the
empty string, narrative consumers SHALL fall back to the character's own name and
the LLM prompt's identity section SHALL be omitted entirely (never filled with a
placeholder).

#### Scenario: Both slots compose with the full-width space
- **WHEN** `compose_title("F級冒險者", "南門新客")` is called
- **THEN** it returns 「F級冒險者　南門新客」

#### Scenario: A single occupied slot omits the separator
- **WHEN** either argument is `None`
- **THEN** the result is the other part alone, and `compose_title(None, None)` returns `""`

### Requirement: The fixed-title lore registry validates and syncs idempotently
`world/lore/titles.py` SHALL hold frozen `FixedTitleDef(key, display_name_zh,
category, flavor_zh, hint_zh, predicate)` entries in a keyed registry mirrored
into Evennia Scripts idempotently at startup, alongside the registry constant
`STARTER_EPITHET` (display 「南門新客」). Load validation SHALL reject: duplicate
keys; empty `hint_zh`; predicates referencing registry faces that do not exist
(element, monster threat tier, quest key, guild rank key, sexual experience
type). Load validation SHALL additionally reject ambiguous equip identifiers —
a duplicate `display_name_zh` or a key equal to another row's display — and a
display longer than 63 code points. The published registry SHALL be an
immutable mapping proxy (no in-place mutation). Predicate families are
declarative (`lineage_complete`, `mastery_owned`, `first_kill_tier`,
`quest_completed`, `guild_rank_reached`, `sexual_experience`,
`counter_threshold`) carrying parameters only.

#### Scenario: A dangling predicate reference fails at load
- **WHEN** a registry row's predicate names a nonexistent quest key
- **THEN** registry load raises naming the row and the dangling reference

#### Scenario: Startup sync twice changes nothing
- **WHEN** the title registry sync runs twice against one database
- **THEN** the mirrored Script state is identical after the second run

### Requirement: Fixed-title grants ride the triggering action's atomic transaction
A registered event-effect planner SHALL evaluate pending predicates against the
step-7 EventLog (non-EventLog faces read through the existing shared read
helpers) and stage fixed-title grants as `PendingEffect` values committed inside
the triggering action's own transaction; collection membership short-circuits
re-grants, so a staged-then-rolled-back grant re-applies naturally when its
events next appear and nothing can be written twice. A successful live grant
SHALL push one OOB notification (「獲得稱號：屠龍者」).

#### Scenario: A predicate-satisfying kill grants inside the same commit
- **WHEN** an action commits an EventLog satisfying a `first_kill_tier` predicate
- **THEN** the fixed entry (with `granted_tick`) is in `title_collection` at that transaction's commit, atomically with the action's other effects

#### Scenario: Planner rollback cannot double-grant
- **WHEN** a staged grant is rolled back and a later action reproduces the same qualifying events
- **THEN** exactly one entry exists afterwards

### Requirement: Guild registration and rank promotion grant paired titles atomically
Each `GUILD_RANK_REGISTRY` row SHALL pair one fixed title. The existing
`world/rules/guild.py::register_adventurer` transaction SHALL grant the
F-rank title (「F級冒險者」)
and the starter epithet 「南門新客」 (a plain epithet entry, `origin_quote` from
the registry constant) in one commit, with no planner or LLM involvement;
re-registration SHALL be an idempotent no-op through the two dedupe rules.
Exam promotions SHALL grant the new rank's title inside `settle_exam_outcome`'s
promotion transaction; a rolled-back promotion removes it. Merit changes, branch
moves, and any future demotion SHALL NOT revoke banked titles.

#### Scenario: Onboarding completes with the composed starter title
- **WHEN** a fresh character completes guild registration
- **THEN** the collection holds fixed 「F級冒險者」 plus epithet 「南門新客」, both slots auto-equipped, and the live full title is 「F級冒險者　南門新客」

#### Scenario: Re-registration is inert
- **WHEN** an already-registered member registers again
- **THEN** collection and equip record are unchanged

#### Scenario: Promotion grants inside the transaction; rollback revokes
- **WHEN** an exam promotion commits, and separately when the same promotion is rolled back
- **THEN** the E-rank title appears exactly in the first case

### Requirement: Slot non-empty is an invariant with auto-equip and no unequip
For each kind, collection-non-empty SHALL imply the matching equip slot is
non-empty. Every mutator that banks an entry (fixed grant, starter pair, and the
future epithet adoption) SHALL auto-equip it into an empty slot within the same
transaction, and SHALL only bank into an occupied slot. No code path, command, or
API SHALL empty a slot (there is no `title clear`). The only empty-slot window is
after character activation and before guild registration.

#### Scenario: First fixed grant auto-equips; later grants bank
- **WHEN** an entity's empty fixed slot receives its first grant, and separately when a second fixed title is granted
- **THEN** the first auto-equips, the second banks without touching the slot

#### Scenario: No mutator sequence empties an occupied slot
- **WHEN** any sequence of F's mutators runs on a collection holding each kind
- **THEN** the state "collection non-empty, slot empty" never occurs

### Requirement: The title equip surface swaps identifiers and never un equips
`title list` SHALL print both blocks — every registry fixed row (locked rows show
`hint_zh`) and every banked epithet — with the current full title.
`title equip fixed <display|key>` and `title equip epithet <display>` SHALL write
the identifier into the matching slot, accepting only entries present in the
collection; unknown, unbanked, or wrong-kind targets SHALL reject deterministically
without listing candidates and without state change. There is no unequip syntax.

#### Scenario: Equipping a banked epithet swaps the slot
- **WHEN** a member with two epithets equips the unequipped one
- **THEN** `title_equipped["epithet"]` names it and the composed full title changes on the next read

#### Scenario: An unbanked display is rejected without an oracle
- **WHEN** `title equip epithet <display>` names a display the collection does not hold
- **THEN** the command rejects with a stable reason and lists no candidate epithets

### Requirement: Narrative consumers compose; predicates read the collection
Narrative and social consumers (character panel header, appraisal prose, status
surface, Director/NPC dialogue prompt context — named `epithet` section, plus up
to five banked entries with their basis quotes when the Director asks for identity
context) SHALL read the composed full title. Mechanical predicates SHALL read the
complete `title_collection` and never the equip slots, so equipping is pure
presentation and unbanked-equipment never affects predicate truth.

#### Scenario: NPCs address the composed title
- **WHEN** a puppeted member with a non-empty full title enters a dialogue or appraisal context
- **THEN** the prompt/prose uses the composed full title

#### Scenario: Predicates ignore equipment
- **WHEN** a predicate-relevant entity satisfies a fixed-title condition without ever equipping it
- **THEN** the predicate reads satisfied from the collection

### Requirement: Epithet nomination fires only at rest points and is throttled
The nomination trigger (the composition-root
`server.title_nomination_service.schedule_epithet_nomination(entity)`; the
transport contract forbids `world/rules` and `commands` from importing
`world/ai`, so scheduling lives in the service and persisting in the rules
writer) SHALL fire only at the four narrative rest points — logout, a
world-clock day boundary while the entity is resting, an examination
pass, and a quest-arc completion — and never during combat settlement. While a
`db.pending_title_ballot` exists, every trigger SHALL return silently (one ballot
at a time; no replacement path). A declined ballot SHALL suppress
renomination for `NOMINATION_COOLDOWN_DAYS` (title-registry constant, initial
value 2) world-clock day boundaries — decline is the only cooldown source,
because ballots never expire; an accepted ballot SHALL NOT start a
cooldown. With the LLM offline, degraded, or past its bounded timeout, the stage
SHALL not fire and fixed titles SHALL be unaffected.

#### Scenario: A pending ballot suppresses every trigger
- **WHEN** any rest-point trigger fires for an entity with a pending ballot
- **THEN** no LLM call is made and the ballot is unchanged

#### Scenario: Decline cools down two day boundaries
- **WHEN** a ballot is declined and day boundaries pass
- **THEN** nominations resume only after the second boundary

#### Scenario: Offline LLM mints nothing
- **WHEN** a trigger fires while the options profile is degraded or absent
- **THEN** the round is void, no ballot is stored, and gameplay is unaffected

### Requirement: The nomination pipeline is 5 candidates through schema and collision filters
The generative stage SHALL ask the Director for exactly five `{display, basis}`
candidates from the recent EventLog summary and SHALL validate them through, in
this order: (1) the closed output schema `{candidates: [{display: str, basis: str}]
x 5}` — malformed JSON, wrong count, or overlong fields void the whole round;
(2) deterministic per-candidate filters, first survivor wins: zh-tw form (2–8
characters, no whitespace, no player-name substring), rejection on equality with
any `FixedTitleDef.display_name_zh`, rejection on equality with any epithet in
the entity's live collection, and in-batch duplicates keeping the first. The
first three survivors form the ballot; one to three survivors ballot as-is; zero
survivors void the round silently. Collision rules SHALL NOT appear in the prompt
text. The generative module SHALL be pure proposal — it returns the filtered
candidates (or nothing) and writes no attribute anywhere; persisting a ballot is
performed solely by the rules-layer nomination writer, which re-checks
suppression after the proposal returns.

#### Scenario: Malformed schema voids the round
- **WHEN** the model returns four candidates, six candidates, or unparseable JSON
- **THEN** no ballot is stored

#### Scenario: A nameless survivor survives deletion history
- **WHEN** a candidate equals an epithet previously deleted from the collection
- **THEN** the live-collection filter passes it (deleted names are renominable)

#### Scenario: Batch duplicates keep the first
- **WHEN** two candidates carry the same display
- **THEN** only the first is kept for the top-three cut

#### Scenario: The generative module persists nothing
- **WHEN** the proposer completes a round with survivors
- **THEN** no attribute outside the rules-layer writer's transaction changed during the proposal

### Requirement: The ballot persists unchanged until consent
The surviving candidates SHALL persist to `db.pending_title_ballot` as
`[{display, basis}]`, surviving logout/relogin and never expiring. The WebClient
SHALL present the OOB ballot menu (title card plus basis quote, buttons 「接受
1／2／3」 and 「放棄」); Telnet SHALL present the same list through the `title`
command family. A player answer arriving after relogin SHALL behave identically to
an answer given in-session.

#### Scenario: A cross-session answer behaves the same
- **WHEN** a player logs out with a pending ballot, returns, and accepts candidate 2
- **THEN** adoption proceeds exactly as an in-session accept

### Requirement: Ballot persistence, acceptance, and decline are rules-layer writers only
The rules layer SHALL own every ballot write: the nomination writer persists a
validated proposal into `db.pending_title_ballot` in its own all-or-nothing step
(a failed persist voids the round, leaving no partial proposal), and
`world/rules/titles.py` SHALL expose `accept_epithet(entity, index)` validating
`index` against the pending ballot, then within one atomic snapshot-registered
transaction: bank the epithet (display, `origin_quote = basis`, `granted_tick`),
auto-equip the epithet slot when empty (F's D8 discipline), and clear the ballot;
a repeated or out-of-range accept SHALL reject with a stable reason and change
nothing. A decline SHALL discard the batch, start the cooldown, record the
declined displays into a bounded per-entity decline log, and emit a
`title_epithet_declined` EventLog entry through the answering surface; the
nomination prompt SHALL digest that decline log as soft-learning context so the
Director's future summaries see what the player rejected, and no programmatic
blacklist SHALL exist anywhere (the decline log is prompt context only, never a
filter rule). No code path outside these three rules-layer writers SHALL change
title state from a ballot.

#### Scenario: Accept banks and auto-equips atomically
- **WHEN** a player accepts candidate 1 while the epithet slot is occupied
- **THEN** the entry banks without touching the slot, and a forced mid-transaction failure restores both attributes

#### Scenario: Decline records for the Director
- **WHEN** a player declines a ballot
- **THEN** a `title_epithet_declined` EventLog entry lists the declined
  displays, no collection entry is created, and the decline log persists them
  so the next nomination prompt digest carries what the player rejected

### Requirement: TitleCodexView is a pure bounded read model for the codex
`world/rules/title_view.py` SHALL expose
`build_title_codex_view(character, *, max_rows, max_display_chars,
max_basis_chars) -> TitleCodexView` reading only the lore registry,
`db.title_collection`, `db.title_equipped`, and `db.pending_title_ballot`:
fixed rows in registry order carrying
`key`/`display`/`category`/`hint_zh` (hint only while locked)/`flavor_zh`
(only when unlocked)/`unlocked`/`granted_tick`, epithet rows newest-first
carrying `display`/`basis`/`granted_tick`/`equipped`/`can_remove`, an
`equipped` dict, a live-composed `full_title`, the `pending_ballot` entries
(degrading to empty when ballot state is malformed, without contaminating the
title rows), and unlocked/total counters. Every string SHALL respect the
passed maxima; the shipped display maxima SHALL equal the storage caps
(64/63) so a rendered action identifier is never a truncated non-matching
string. The view SHALL compute without mutating and repeat byte-identically
while state is unchanged. OOB constants `TITLE_MAX_ROWS` /
`TITLE_MAX_DISPLAY_CHARS` / `TITLE_MAX_BASIS_CHARS` (and the title-category
enum) SHALL be mirrored across all four mirrors like every OOB surface.

#### Scenario: Locked rows show hints, unlocked rows show flavor
- **WHEN** a view is built for a character holding part of the registry
- **THEN** locked rows carry `hint_zh` and no flavor, unlocked rows carry flavor and no hint, and counters equal the unlocked/total split

#### Scenario: Overlong basis text is clipped to the cap
- **WHEN** an epithet's `origin_quote` exceeds `max_basis_chars`
- **THEN** the row's basis is clipped to the cap and remains a contiguous prefix of the quote

### Requirement: The codex OOB payload and WebClient window are server-authored
The `title` OOB schema v1 SHALL carry
`{schema_version, fixed_rows, epithet_rows, equipped, full_title, unlocked,
total, pending_ballot}` rendered by the WebClient as a big window: header with
the live full-title preview; 「稱號」block with category tabs (戰鬥／法術／探索／公會／
風流韻事), locked cards showing 🔒 + hint, clicking an unlocked fixed card
requesting that fixed equip; 「異名」block with click-to-equip, ★ marking the
equipped epithet, and the 「移除」 button rendered from the row's server-computed
`can_remove` flag with no client-side rules; a 「提名中」tab presenting G's pending
ballot with the accept/decline buttons; no 卸裝 control anywhere. The preview
SHALL update on every successful equip.

#### Scenario: Locked cards offer no affordance
- **WHEN** the window renders a row whose `unlocked` is false
- **THEN** the card shows the lock and hint, and clicking it causes no state change

#### Scenario: The remove button follows the flag
- **WHEN** an epithet row carries `can_remove = false`
- **THEN** no 移除 control renders for it, and the client evaluates no gate logic itself

### Requirement: Epithet removal is the only delete path and gates precede confirmation
`world/rules/titles.py::remove_epithet(entity, display)` SHALL be the system's
only collection-deleting API, validating in one pass before any review state
exists, in this precedence: unknown display or wrong kind ⇒ stable rejection;
it is the last remaining epithet ⇒ `TITLE_LAST_EPITHET` (under the D8
invariant the sole epithet is necessarily the equipped one, so this gate MUST
be evaluated first for the one-epithet case to name the true reason);
`display` equals the equipped epithet ⇒ `TITLE_EQUIPPED_UNREMOVABLE` — neither
gate code ever enters the confirm flow. Only an un-gated target echoes review
info (display + basis) for the two-step Telnet path (`title remove epithet
<display>` then literal `confirm` suffix; a display containing the literal
final token quotes it so the suffix stays unambiguous; any other continuation
cancels without state change), after which the executing call re-validates
both gates and, within one snapshot-registered transaction, removes the entry,
records `{tick, display}` into the bounded durable removal log
(`title_epithet_removals`, the Director-facing feed mirroring the decline
log), and emits the renderable `title_epithet_removed`
(actor, display, tick) EventLog. Slots SHALL never be touched by removal.
Fixed titles SHALL expose no delete API, command, or code path — a structural
test asserts absence. Removal is irreversible; there is no recycle bin, and
the removed name becomes nominatable again through G's live-collection filter.

#### Scenario: Equipped epithet refuses at gate one
- **WHEN** `title remove epithet <equipped display>` is attempted
- **THEN** `TITLE_EQUIPPED_UNREMOVABLE` is returned and no review info is echoed

#### Scenario: The last epithet refuses
- **WHEN** a collection holding exactly one epithet attempts its removal
- **THEN** `TITLE_LAST_EPITHET` is returned and the collection is unchanged

#### Scenario: Confirm removes and records; any other continuation cancels
- **WHEN** an un-gated removal is confirmed with the literal `confirm` suffix, and separately answered with anything else
- **THEN** the confirmed call removes the entry, leaves both slots untouched, and appends `title_epithet_removed`; the other leaves state byte-identical

#### Scenario: Fixed titles have no delete surface
- **WHEN** the structural absence test scans titles modules and command surfaces
- **THEN** no fixed-title delete API, command, or code path exists

### Requirement: Codex surfaces remain consistent across sessions
Collection, equip record, removal log, and pending ballot are persistent
attributes, so the codex window — including the 「提名中」tab and every
`can_remove` flag — SHALL render identically after relogin or reload; a removal
executed in one session SHALL be reflected in the next session's view and in
the durable removal log.

#### Scenario: Post-relogin view matches the pre-logout view
- **WHEN** a player removes an epithet, logs out, and reopens the codex
- **THEN** the row is gone, counters updated, and the ballot tab state is unchanged by the logout
