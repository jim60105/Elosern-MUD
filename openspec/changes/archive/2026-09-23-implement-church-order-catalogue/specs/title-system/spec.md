## ADDED Requirements

### Requirement: The church redeemed-count predicate family evaluates the redeemed ledger only
`TitlePredicateFamily` SHALL gain exactly one member, `church_skills_redeemed`, carrying exactly one parameter: an integer threshold (registered on the `TitlePredicate` parameter face and its single-family validation like every existing family). `predicate_satisfied` SHALL evaluate it as `len(db.church.redeemed) >= threshold`, reading persistent state through the no-create helper only (an entity with no church ledger evaluates to false without materializing one; writes never occur in the evaluator). The count SHALL be the redeemed catalogue keys only — `saintess_vessel` is never in `redeemed` by the church capability's negative-set construction, so the office can never unlock a title through this family, and the family SHALL NOT reference any other church state (merit, enrollment tick, daily counters).

#### Scenario: The family fires exactly at the threshold
- **WHEN** an entity with `len(db.church.redeemed)` of exactly k is evaluated against thresholds k and k+1
- **THEN** the family is satisfied for k and unsatisfied for k+1

#### Scenario: The vessel never counts
- **WHEN** a female royal saintess who holds `saintess_vessel` but has redeemed nothing is evaluated against any positive threshold
- **THEN** the family is unsatisfied

#### Scenario: An unenrolled entity fails closed without writes
- **WHEN** an entity with no `db.church` ledger is evaluated
- **THEN** the result is false and no ledger or any other state is created

### Requirement: The clergy title ladder unlocks by redeemed count and never displays 聖女
The fixed-title registry SHALL carry a five-row clergy ladder in the 聖職 category, one row per rung (虔信者／修女／神官／主教／樞機), each row's predicate a `church_skills_redeemed` integer threshold. The five thresholds are tuning placeholders: their finals SHALL be decided and recorded by this change's tuning task (design baseline 3／6／10／15／20, strictly ascending) in BOTH the registry rows and this requirement's scenarios before archive — the shipped rows and the recorded finals SHALL agree. Grants ride the existing fixed-title machinery verbatim — declarative predicate families, auto-unlock and auto-equip of an empty slot, display-only value, and NO other system may use these titles as a prerequisite. No fixed-title row of ANY category SHALL display or otherwise name the 聖女 office: the registry loader/data-contract gate rejects any row whose display contains 聖女, reaffirming the saintess-vessel spec's office-as-prose decision globally rather than for the ladder alone. Ladder rows carry non-empty `hint_zh` and pass the registry's one-row-one-test correspondence tests.

#### Scenario: Each rung unlocks exactly at its count
- **WHEN** a character's redeemed count crosses each ladder threshold (exactly at, and one below)
- **THEN** the matching title is banked with the fixed slot auto-equipped at the threshold and remains locked one below it

#### Scenario: The 聖女 display ban is a global registry gate
- **WHEN** a planted fixed-title row of any category contains 聖女 in its display name, key, flavor, or hint
- **THEN** registry validation rejects it, and every shipped fixed-title row — ladder or otherwise — passes the gate with non-聖女 text

#### Scenario: The ladder is display-only
- **WHEN** the codebase is searched for title state consumed as a prerequisite
- **THEN** no system gates anything on a clergy title key or display

## MODIFIED Requirements

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
`counter_threshold`, `church_skills_redeemed`) carrying parameters only;
`church_skills_redeemed` carries the integer `threshold` parameter and
references no external registry face. The codex `category` vocabulary SHALL be
extended with the 聖職 (`clergy`) member, and the shipped clergy ladder rows
validate against it at module load exactly as the guild rows validate against
the guild-rank face.

#### Scenario: A dangling predicate reference fails at load
- **WHEN** a registry row's predicate names a nonexistent quest key
- **THEN** registry load raises naming the row and the dangling reference

#### Scenario: Startup sync twice changes nothing
- **WHEN** the title registry sync runs twice against one database
- **THEN** the mirrored Script state is identical after the second run

#### Scenario: A clergy-category row is accepted; a foreign category is not
- **WHEN** a ladder row declares the 聖職 category, and a planted row declares a category outside the closed enum
- **THEN** the ladder row loads and the planted row raises naming the row

### Requirement: The codex OOB payload and WebClient window are server-authored
The `title` OOB schema v1 SHALL carry
`{schema_version, fixed_rows, epithet_rows, equipped, full_title, unlocked,
total, pending_ballot}` rendered by the WebClient as a big window: header with
the live full-title preview; 「稱號」block with category tabs (戰鬥／法術／探索／公會／
聖職／風流韻事), locked cards showing 🔒 + hint, clicking an unlocked fixed card
requesting that fixed equip; 「異名」block with click-to-equip, ★ marking the
equipped epithet, and the 「移除」 button rendered from the row's server-computed
`can_remove` flag with no client-side rules; a 「提名中」tab presenting G's pending
ballot with the accept/decline buttons; no 卸裝 control anywhere. The category
enum SHALL stay mirrored across all its faces — the Python `TitleCategory`, the
presentation mirror, the client `constants.js` validator enum, and its protocol
test — and the panel validator SHALL reject a payload carrying a category
outside the extended closed set. The preview SHALL update on every successful
equip.

#### Scenario: Locked cards offer no affordance
- **WHEN** the window renders a row whose `unlocked` is false
- **THEN** the card shows the lock and hint, and clicking it causes no state change

#### Scenario: The remove button follows the flag
- **WHEN** an epithet row carries `can_remove = false`
- **THEN** no 移除 control renders for it, and the client evaluates no gate logic itself

#### Scenario: The clergy tab renders and an unknown category is rejected
- **WHEN** a payload with 聖職-category rows reaches the panel, and separately a payload whose row category is outside the extended enum
- **THEN** the first renders under its tab with the ladder rows, and the client validator rejects the second rather than rendering it
