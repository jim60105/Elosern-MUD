## ADDED Requirements

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
SHALL read exactly as `[]` and `{"fixed": None, "epithet": None}`.

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
type). Predicate families are declarative (`lineage_complete`, `mastery_owned`,
`first_kill_tier`, `quest_completed`, `guild_rank_reached`, `sexual_experience`,
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
`register_guild_member` transaction SHALL grant the F-rank title (「F級冒險者」)
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
