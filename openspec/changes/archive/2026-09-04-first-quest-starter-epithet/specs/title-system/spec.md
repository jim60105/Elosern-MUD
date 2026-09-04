# title-system — delta

## MODIFIED Requirements

### Requirement: Guild registration and rank promotion grant paired titles atomically
Each `GUILD_RANK_REGISTRY` row SHALL pair one fixed title. The existing
`world/rules/guild.py::register_adventurer` transaction SHALL grant the
F-rank title (「F級冒險者」)
in one commit, with no planner or LLM involvement;
re-registration SHALL be an idempotent no-op through the fixed-key dedupe rule.
The starter epithet 「南門新客」 SHALL NOT be granted at registration: it is
granted by `world/rules/titles.py::grant_first_quest_epithet` inside the
actor's first guild reward-claim transaction (quest-reward-settlement), through
the regular `bank_epithet` writer. Exam promotions SHALL grant the new rank's
title inside `settle_exam_outcome`'s promotion transaction; a rolled-back
promotion removes it. Merit changes, branch
moves, and any future demotion SHALL NOT revoke banked titles.

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

### Requirement: Slot non-empty is an invariant with auto-equip and no unequip
For each kind, collection-non-empty SHALL imply the matching equip slot is
non-empty. Every mutator that banks an entry (fixed grant, the first-quest
epithet grant, and the
future epithet adoption) SHALL auto-equip it into an empty slot within the same
transaction, and SHALL only bank into an occupied slot. No code path, command, or
API SHALL empty a slot (there is no `title clear`). The only empty-slot window
for the fixed slot is after character activation and before guild registration;
the only empty-slot window for the epithet slot is before the member's first
completed guild reward claim.

#### Scenario: First fixed grant auto-equips; later grants bank
- **WHEN** an entity's empty fixed slot receives its first grant, and separately when a second fixed title is granted
- **THEN** the first auto-equips, the second banks without touching the slot

#### Scenario: No mutator sequence empties an occupied slot
- **WHEN** any sequence of F's mutators runs on a collection holding each kind
- **THEN** the state "collection non-empty, slot empty" never occurs
