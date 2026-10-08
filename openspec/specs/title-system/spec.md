# title-system Specification

## Purpose

Define deterministic title storage, the fixed-title lore registry, transactional title grants, the swap-only equip surface, and the narrative consumers that compose the player-facing full title (稱號　異名).

## Requirements

### Requirement: Title state is a two-kind collection and a two-slot equip record
`db.title_collection` SHALL be a list of entries identified by `(kind, key | display)`: fixed entries `{"kind": "fixed", "key", "granted_tick"}` and epithet entries `{"kind": "epithet", "display", "origin_quote", "granted_tick"}`. Fixed keys SHALL appear at most once (duplicate grants are silent no-ops); epithet displays SHALL be unique within the collection. `db.title_equipped` SHALL be `{"fixed": <fixed key or None>, "epithet": <display or None>}`, storing identifiers (never copies).

#### Scenario: Duplicate fixed grant is a no-op
- **WHEN** an entity already holding fixed key `g_f_rank` is granted it again
- **THEN** the collection and equip record are byte-identical to before

#### Scenario: Rolled-back grants restore both attributes
- **WHEN** a triggering action commits a title write and a later failure restores the action snapshot
- **THEN** `title_collection` and `title_equipped` return to their pre-action values

#### Scenario: Fixed entries are never removable
- **WHEN** the structural test scans for any delete API, command, or code path over fixed entries
- **THEN** none exists

#### Scenario: Snapshot registration precedes writers
- **WHEN** any title writer is introduced
- **THEN** `title_collection` and `title_equipped` are already registered on the snapshot/restore surface

#### Scenario: Missing attributes read as empty
- **WHEN** the attributes have never been written
- **THEN** they read exactly as `[]` and `{"fixed": None, "epithet": None}`

#### Scenario: Bank writers validate every input before any write
- **WHEN** a bank write is attempted with a fixed key that names no registry row, blank display or origin quote, an over-cap display, or a negative/non-integer `granted_tick`
- **THEN** the writer raises `TitleDataError` and state is byte-identical

### Requirement: compose_title is the single pure composition of the full title
`world/rules/titles.py` SHALL define `compose_title(fixed: str | None, epithet: str | None) -> str` joining the non-empty parts fixed-first, epithet-second, with a full-width space (「　」), returning the empty string when both slots are empty. No consumer SHALL store a composed copy; every read composes live from the two slots' identifiers.

#### Scenario: Both slots compose with the full-width space
- **WHEN** `compose_title("F級冒險者", "南門新客")` is called
- **THEN** it returns 「F級冒險者　南門新客」

#### Scenario: A single occupied slot omits the separator
- **WHEN** either argument is `None`
- **THEN** the result is the other part alone, and `compose_title(None, None)` returns `""`

#### Scenario: The empty composition falls back to the name, never a placeholder
- **WHEN** the composition is the empty string
- **THEN** narrative consumers fall back to the character's own name and the LLM prompt's identity section is omitted entirely, never filled with a placeholder

### Requirement: The fixed-title lore registry validates and syncs idempotently
`world/lore/titles.py` SHALL hold frozen `FixedTitleDef(key, display_name_zh, category, flavor_zh, hint_zh, predicate)` entries in a keyed registry mirrored into Evennia Scripts idempotently at startup, alongside the registry constant `STARTER_EPITHET` (display 「南門新客」). Load validation SHALL reject malformed or ambiguous registries before anything is published.

#### Scenario: A dangling predicate reference fails at load
- **WHEN** a registry row's predicate names a nonexistent quest key
- **THEN** registry load raises naming the row and the dangling reference

#### Scenario: Startup sync twice changes nothing
- **WHEN** the title registry sync runs twice against one database
- **THEN** the mirrored Script state is identical after the second run

#### Scenario: A clergy-category row is accepted; a foreign category is not
- **WHEN** a ladder row declares the 聖職 category, and a planted row declares a category outside the closed enum
- **THEN** the ladder row loads and the planted row raises naming the row

#### Scenario: Duplicate keys and empty hints fail at load
- **WHEN** the registry carries a duplicate key or a row with empty `hint_zh`, or a predicate references a nonexistent registry face (element, monster threat tier, quest key, guild rank key, sexual experience type)
- **THEN** load validation rejects the registry

#### Scenario: Ambiguous equip identifiers fail at load
- **WHEN** a `display_name_zh` is duplicated or a key equals another row's display
- **THEN** load validation rejects the registry, keeping every equip identifier unambiguous

#### Scenario: An overlong display fails at load
- **WHEN** a row's display is longer than 63 code points
- **THEN** load validation rejects the registry

#### Scenario: The published registry is immutable
- **WHEN** a caller attempts in-place mutation of the published registry
- **THEN** the immutable mapping proxy refuses it

#### Scenario: Predicate families are declarative
- **WHEN** the predicate families (`lineage_complete`, `mastery_owned`, `first_kill_tier`, `quest_completed`, `guild_rank_reached`, `sexual_experience`, `counter_threshold`, `church_skills_redeemed`) are inspected
- **THEN** each carries parameters only; `church_skills_redeemed` carries the integer `threshold` parameter and references no external registry face

#### Scenario: The clergy category joins the codex vocabulary
- **WHEN** the shipped clergy ladder rows validate at module load
- **THEN** they validate against the codex `category` vocabulary extended with the 聖職 (`clergy`) member, exactly as the guild rows validate against the guild-rank face

### Requirement: Fixed-title grants ride the triggering action's atomic transaction
A registered event-effect planner SHALL evaluate pending predicates against the step-7 EventLog (non-EventLog faces read through the existing shared read helpers) and stage fixed-title grants as `PendingEffect` values committed inside the triggering action's own transaction; collection membership short-circuits re-grants, so a staged-then-rolled-back grant re-applies naturally when its events next appear and nothing can be written twice.

#### Scenario: A predicate-satisfying kill grants inside the same commit
- **WHEN** an action commits an EventLog satisfying a `first_kill_tier` predicate
- **THEN** the fixed entry (with `granted_tick`) is in `title_collection` at that transaction's commit, atomically with the action's other effects

#### Scenario: Planner rollback cannot double-grant
- **WHEN** a staged grant is rolled back and a later action reproduces the same qualifying events
- **THEN** exactly one entry exists afterwards

#### Scenario: A live grant pushes one notification
- **WHEN** a fixed-title grant commits successfully on a live session
- **THEN** one OOB notification (「獲得稱號：屠龍者」) is pushed

### Requirement: Guild registration and rank promotion grant paired titles atomically
Each `GUILD_RANK_REGISTRY` row SHALL pair one fixed title. The existing `world/rules/guild.py::register_adventurer` transaction SHALL grant the F-rank title (「F級冒險者」) in one commit, with no planner or LLM involvement. Exam promotions SHALL grant the new rank's title inside `settle_exam_outcome`'s promotion transaction; a rolled-back promotion removes it.

#### Scenario: Registration banks the rank title only
- **WHEN** a fresh character completes guild registration
- **THEN** the collection holds fixed 「F級冒險者」 with the fixed slot auto-equipped, no epithet entry exists, and the live full title is 「F級冒險者」

#### Scenario: The composed starter title arrives at the first reward claim
- **WHEN** a registered member completes their first guild reward claim
- **THEN** the collection holds fixed 「F級冒險者」 plus epithet 「南門新客」, both slots auto-equipped, and the live full title is 「F級冒險者　南門新客」

#### Scenario: Re-registration is inert
- **WHEN** an already-registered member registers again
- **THEN** collection and equip record are unchanged

#### Scenario: Promotion grants inside the transaction; rollback revokes
- **WHEN** an exam promotion commits, and separately when the same promotion is rolled back
- **THEN** the E-rank title appears exactly in the first case

#### Scenario: Re-registration dedupes through the fixed-key rule
- **WHEN** a member registers again
- **THEN** the grant is an idempotent no-op through the fixed-key dedupe rule

#### Scenario: The starter epithet is granted at the first reward claim, not registration
- **WHEN** guild registration completes
- **THEN** the starter epithet 「南門新客」 is not granted; it is granted by `world/rules/titles.py::grant_first_quest_epithet` inside the actor's first guild reward-claim transaction (quest-reward-settlement), through the regular `bank_epithet` writer

#### Scenario: Non-promotion guild changes never revoke titles
- **WHEN** merit changes, branch moves, or any future demotion occurs
- **THEN** banked titles are not revoked


### Requirement: Slot non-empty is an invariant with auto-equip and no unequip
For each kind, collection-non-empty SHALL imply the matching equip slot is non-empty. Every mutator that banks an entry (fixed grant, the first-quest epithet grant, and the future epithet adoption) SHALL auto-equip it into an empty slot within the same transaction, and SHALL only bank into an occupied slot. No code path, command, or API SHALL empty a slot (there is no `title clear`).

#### Scenario: First fixed grant auto-equips; later grants bank
- **WHEN** an entity's empty fixed slot receives its first grant, and separately when a second fixed title is granted
- **THEN** the first auto-equips, the second banks without touching the slot

#### Scenario: No mutator sequence empties an occupied slot
- **WHEN** any sequence of F's mutators runs on a collection holding each kind
- **THEN** the state "collection non-empty, slot empty" never occurs

#### Scenario: The empty-slot windows are bounded
- **WHEN** the entity's lifecycle is examined for empty slots
- **THEN** the only empty-slot window for the fixed slot is after character activation and before guild registration, and the only empty-slot window for the epithet slot is before the member's first completed guild reward claim


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
The nomination trigger — the composition-root `server.title_nomination_service.schedule_epithet_nomination(entity)` — SHALL fire only at the four narrative rest points — logout, a world-clock day boundary while the entity is resting, an examination pass, and a quest-arc completion — and never during combat settlement. While a `db.pending_title_ballot` exists, every trigger SHALL return silently (one ballot at a time; no replacement path).

#### Scenario: A pending ballot suppresses every trigger
- **WHEN** any rest-point trigger fires for an entity with a pending ballot
- **THEN** no LLM call is made and the ballot is unchanged

#### Scenario: Scheduling lives in the service, persisting in the rules writer
- **WHEN** the nomination trigger's placement is checked against the transport contract
- **THEN** the contract's ban on `world/rules` and `commands` importing `world/ai` holds — scheduling lives in the composition-root service and persisting in the rules writer

#### Scenario: Decline cools down two day boundaries
- **WHEN** a ballot is declined and day boundaries pass
- **THEN** nominations resume only after the second boundary

#### Scenario: Offline LLM mints nothing
- **WHEN** a trigger fires while the options profile is degraded or absent
- **THEN** the round is void, no ballot is stored, and gameplay is unaffected

#### Scenario: Only decline starts a cooldown
- **WHEN** a ballot is declined, and separately when one is accepted
- **THEN** the decline suppresses renomination for `NOMINATION_COOLDOWN_DAYS` (title-registry constant, initial value 2) world-clock day boundaries — decline is the only cooldown source, because ballots never expire — and the accepted ballot starts no cooldown

#### Scenario: An unavailable LLM never fires the stage
- **WHEN** the LLM is offline, degraded, or past its bounded timeout
- **THEN** the stage does not fire and fixed titles are unaffected

### Requirement: The nomination pipeline is 5 candidates through schema and collision filters
The generative stage SHALL ask the Director for exactly five `{display, basis}` candidates from the recent EventLog summary and SHALL validate them through, in this order: (1) the closed output schema `{candidates: [{display: str, basis: str}] x 5}` — malformed JSON, wrong count, or overlong fields void the whole round; (2) deterministic per-candidate filters, first survivor wins.

#### Scenario: Malformed schema voids the round
- **WHEN** the model returns four candidates, six candidates, or unparseable JSON
- **THEN** no ballot is stored

#### Scenario: The per-candidate filters are deterministic
- **WHEN** the per-candidate filters run
- **THEN** they enforce zh-tw form (2–8 characters, no whitespace, no player-name substring), reject equality with any `FixedTitleDef.display_name_zh`, reject equality with any epithet in the entity's live collection, and keep the first of in-batch duplicates

#### Scenario: A nameless survivor survives deletion history
- **WHEN** a candidate equals an epithet previously deleted from the collection
- **THEN** the live-collection filter passes it (deleted names are renominable)

#### Scenario: Batch duplicates keep the first
- **WHEN** two candidates carry the same display
- **THEN** only the first is kept for the top-three cut

#### Scenario: The generative module persists nothing
- **WHEN** the proposer completes a round with survivors
- **THEN** no attribute outside the rules-layer writer's transaction changed during the proposal

#### Scenario: Survivor count decides the ballot
- **WHEN** the filters run over the five candidates
- **THEN** the first three survivors form the ballot, one to three survivors ballot as-is, and zero survivors void the round silently

#### Scenario: Collision rules stay out of the prompt
- **WHEN** the nomination prompt text is inspected
- **THEN** no collision rule appears in it

#### Scenario: Only the rules-layer writer persists the ballot
- **WHEN** the pure-proposal module returns the filtered candidates (or nothing)
- **THEN** persisting a ballot is performed solely by the rules-layer nomination writer, which re-checks suppression after the proposal returns

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
The rules layer SHALL own every ballot write: the nomination writer persists a validated proposal into `db.pending_title_ballot` in its own all-or-nothing step (a failed persist voids the round, leaving no partial proposal). No code path outside these three rules-layer writers SHALL change title state from a ballot.

#### Scenario: Accept banks and auto-equips atomically
- **WHEN** a player accepts candidate 1 while the epithet slot is occupied
- **THEN** the entry banks without touching the slot, and a forced mid-transaction failure restores both attributes

#### Scenario: Decline records for the Director
- **WHEN** a player declines a ballot
- **THEN** a `title_epithet_declined` EventLog entry lists the declined
  displays, no collection entry is created, and the decline log persists them
  so the next nomination prompt digest carries what the player rejected

#### Scenario: accept_epithet validates and commits atomically
- **WHEN** `world/rules/titles.py::accept_epithet(entity, index)` is called
- **THEN** it validates `index` against the pending ballot, then within one atomic snapshot-registered transaction banks the epithet (display, `origin_quote = basis`, `granted_tick`), auto-equips the epithet slot when empty (F's D8 discipline), and clears the ballot

#### Scenario: A repeated or out-of-range accept changes nothing
- **WHEN** `accept_epithet` is called again after acceptance or with an out-of-range `index`
- **THEN** it rejects with a stable reason and changes nothing

#### Scenario: A decline discards, cools down, and logs
- **WHEN** a player declines a ballot
- **THEN** the batch is discarded, the cooldown starts, the declined displays are recorded into a bounded per-entity decline log, and a `title_epithet_declined` EventLog entry is emitted through the answering surface

#### Scenario: The decline log is prompt context, never a filter
- **WHEN** the nomination prompt is built and the codebase is searched for blacklist logic
- **THEN** the prompt digests the decline log as soft-learning context so the Director's future summaries see what the player rejected, and no programmatic blacklist exists anywhere (the decline log is prompt context only, never a filter rule)

### Requirement: TitleCodexView is a pure bounded read model for the codex
`world/rules/title_view.py` SHALL expose `build_title_codex_view(character, *, max_rows, max_display_chars, max_basis_chars) -> TitleCodexView` reading only the lore registry, `db.title_collection`, `db.title_equipped`, and `db.pending_title_ballot`. The view SHALL compute without mutating and repeat byte-identically while state is unchanged.

#### Scenario: Locked rows show hints, unlocked rows show flavor
- **WHEN** a view is built for a character holding part of the registry
- **THEN** locked rows carry `hint_zh` and no flavor, unlocked rows carry flavor and no hint, and counters equal the unlocked/total split

#### Scenario: Overlong basis text is clipped to the cap
- **WHEN** an epithet's `origin_quote` exceeds `max_basis_chars`
- **THEN** the row's basis is clipped to the cap and remains a contiguous prefix of the quote

#### Scenario: Fixed rows carry the registry shape in registry order
- **WHEN** the view renders fixed rows
- **THEN** they appear in registry order carrying `key`/`display`/`category`/`hint_zh` (hint only while locked)/`flavor_zh` (only when unlocked)/`unlocked`/`granted_tick`

#### Scenario: Epithet rows carry the banked shape newest-first
- **WHEN** the view renders epithet rows
- **THEN** they appear newest-first carrying `display`/`basis`/`granted_tick`/`equipped`/`can_remove`

#### Scenario: The view carries equip, composition, ballot, and counters
- **WHEN** the view is built
- **THEN** it carries an `equipped` dict, a live-composed `full_title`, the `pending_ballot` entries, and unlocked/total counters

#### Scenario: Malformed ballot state degrades the ballot only
- **WHEN** ballot state is malformed
- **THEN** `pending_ballot` degrades to empty without contaminating the title rows

#### Scenario: Rendered strings respect the maxima and the shipped caps
- **WHEN** the view renders any string
- **THEN** it respects the passed maxima, and the shipped display maxima equal the storage caps (64/63) so a rendered action identifier is never a truncated non-matching string

#### Scenario: The codex OOB constants are mirrored
- **WHEN** the OOB constants `TITLE_MAX_ROWS` / `TITLE_MAX_DISPLAY_CHARS` / `TITLE_MAX_BASIS_CHARS` (and the title-category enum) are checked
- **THEN** they are mirrored across all four mirrors like every OOB surface

### Requirement: The codex OOB payload and WebClient window are server-authored
The `title` OOB schema v1 SHALL carry `{schema_version, fixed_rows, epithet_rows, equipped, full_title, unlocked, total, pending_ballot}` rendered by the WebClient as a big window: header with the live full-title preview; 「稱號」block with category tabs (戰鬥／法術／探索／公會／聖職／風流韻事), locked cards showing 🔒 + hint, and clicking an unlocked fixed card requesting that fixed equip.

#### Scenario: Locked cards offer no affordance
- **WHEN** the window renders a row whose `unlocked` is false
- **THEN** the card shows the lock and hint, and clicking it causes no state change

#### Scenario: The remove button follows the flag
- **WHEN** an epithet row carries `can_remove = false`
- **THEN** no 移除 control renders for it, and the client evaluates no gate logic itself

#### Scenario: The clergy tab renders and an unknown category is rejected
- **WHEN** a payload with 聖職-category rows reaches the panel, and separately a payload whose row category is outside the extended enum
- **THEN** the first renders under its tab with the ladder rows, and the client validator rejects the second rather than rendering it

#### Scenario: The 異名 block renders equip marks and server-driven removal
- **WHEN** the window renders the 「異名」block
- **THEN** rows are click-to-equip, ★ marks the equipped epithet, and the 「移除」 button renders from the row's server-computed `can_remove` flag with no client-side rules

#### Scenario: The 提名中 tab carries the ballot and there is no unequip control
- **WHEN** the window renders G's pending ballot
- **THEN** the 「提名中」tab presents it with the accept/decline buttons, and no 卸裝 control exists anywhere in the window

#### Scenario: The category enum stays mirrored across all its faces
- **WHEN** the title category enum is checked
- **THEN** the Python `TitleCategory`, the presentation mirror, the client `constants.js` validator enum, and its protocol test agree, and the panel validator rejects a payload carrying a category outside the extended closed set

#### Scenario: The preview tracks every equip
- **WHEN** an equip request succeeds
- **THEN** the live full-title preview updates

### Requirement: Epithet removal is the only delete path and gates precede confirmation
`world/rules/titles.py::remove_epithet(entity, display)` SHALL be the system's only collection-deleting API, validating in one pass before any review state exists, in this precedence: unknown display or wrong kind ⇒ stable rejection; it is the last remaining epithet ⇒ `TITLE_LAST_EPITHET`; `display` equals the equipped epithet ⇒ `TITLE_EQUIPPED_UNREMOVABLE` — neither gate code ever enters the confirm flow.

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

#### Scenario: The last-epithet gate is evaluated first under the D8 invariant
- **WHEN** the one-epithet case is gated
- **THEN** the last-epithet gate is evaluated first — under the D8 invariant the sole epithet is necessarily the equipped one — so the rejection names the true reason

#### Scenario: Only an un-gated target echoes review info for the two-step Telnet path
- **WHEN** a removal target passes both gates
- **THEN** review info (display + basis) is echoed for `title remove epithet <display>` followed by the literal `confirm` suffix; a display containing the literal final token quotes it so the suffix stays unambiguous, and any other continuation cancels without state change

#### Scenario: The executing call re-validates and records durably
- **WHEN** a confirmed removal executes
- **THEN** it re-validates both gates and, within one snapshot-registered transaction, removes the entry, records `{tick, display}` into the bounded durable removal log (`title_epithet_removals`, the Director-facing feed mirroring the decline log), and emits the renderable `title_epithet_removed` (actor, display, tick) EventLog

#### Scenario: Removal never touches slots
- **WHEN** any removal runs
- **THEN** the equip slots are never touched

#### Scenario: Removal is irreversible yet the name is renominable
- **WHEN** an epithet has been removed
- **THEN** there is no recycle bin, and the removed name becomes nominatable again through G's live-collection filter

### Requirement: Codex surfaces remain consistent across sessions
Collection, equip record, removal log, and pending ballot are persistent
attributes, so the codex window — including the 「提名中」tab and every
`can_remove` flag — SHALL render identically after relogin or reload; a removal
executed in one session SHALL be reflected in the next session's view and in
the durable removal log.

#### Scenario: Post-relogin view matches the pre-logout view
- **WHEN** a player removes an epithet, logs out, and reopens the codex
- **THEN** the row is gone, counters updated, and the ballot tab state is unchanged by the logout

### Requirement: The church redeemed-count predicate family evaluates the redeemed ledger only
`TitlePredicateFamily` SHALL gain exactly one member, `church_skills_redeemed`, carrying exactly one parameter: an integer threshold (registered on the `TitlePredicate` parameter face and its single-family validation like every existing family). `predicate_satisfied` SHALL evaluate it as `len(db.church.redeemed) >= threshold`, reading persistent state through the no-create helper only.

#### Scenario: The family fires exactly at the threshold
- **WHEN** an entity with `len(db.church.redeemed)` of exactly k is evaluated against thresholds k and k+1
- **THEN** the family is satisfied for k and unsatisfied for k+1

#### Scenario: The vessel never counts
- **WHEN** a female royal saintess who holds `saintess_vessel` but has redeemed nothing is evaluated against any positive threshold
- **THEN** the family is unsatisfied

#### Scenario: An unenrolled entity fails closed without writes
- **WHEN** an entity with no `db.church` ledger is evaluated
- **THEN** the result is false and no ledger or any other state is created

#### Scenario: The evaluator never writes
- **WHEN** `predicate_satisfied` evaluates the family
- **THEN** no writes occur in the evaluator

#### Scenario: The count is redeemed catalogue keys only
- **WHEN** the family counts toward a threshold
- **THEN** only the redeemed catalogue keys count — `saintess_vessel` is never in `redeemed` by the church capability's negative-set construction, so the office can never unlock a title through this family, and the family references no other church state

### Requirement: The clergy title ladder unlocks by redeemed count and never displays 聖女
The fixed-title registry SHALL carry a five-row clergy ladder in the 聖職 category, one row per rung (虔信者／修女／神官／主教／樞機), each row's predicate a `church_skills_redeemed` integer threshold. The five thresholds are tuning placeholders (design baseline 3／6／10／15／20, strictly ascending). NO other system may use these titles as a prerequisite.

#### Scenario: Each rung unlocks exactly at its count
- **WHEN** a character's redeemed count crosses each ladder threshold (exactly at, and one below)
- **THEN** the matching title is banked with the fixed slot auto-equipped at the threshold and remains locked one below it

#### Scenario: The 聖女 display ban is a global registry gate
- **WHEN** a planted fixed-title row of any category contains 聖女 in its display name, key, flavor, or hint
- **THEN** registry validation rejects it, and every shipped fixed-title row — ladder or otherwise — passes the gate with non-聖女 text

#### Scenario: The ladder is display-only
- **WHEN** the codebase is searched for title state consumed as a prerequisite
- **THEN** no system gates anything on a clergy title key or display

#### Scenario: Threshold finals are recorded by the tuning task
- **WHEN** this change's tuning task decides the five threshold finals
- **THEN** they are recorded in BOTH the registry rows and this requirement's scenarios before archive, and the shipped rows and the recorded finals agree

#### Scenario: Ladder grants ride the existing machinery verbatim
- **WHEN** a clergy ladder title is earned
- **THEN** the existing fixed-title machinery applies verbatim — declarative predicate families, auto-unlock and auto-equip of an empty slot, and display-only value

#### Scenario: The 聖女 office stays prose
- **WHEN** the shipped registry is audited for any naming of the 聖女 office
- **THEN** no fixed-title row of ANY category displays or otherwise names it — the office stays prose per the saintess-vessel spec (reaffirmed, design §9)
