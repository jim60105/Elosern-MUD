## Purpose

Grants skill ownership when an entity's practice proficiency across *other* lineage trees reaches declared depths, using one declarative rule table that can equally grant a single passive or open an entire new lineage tree by granting its root nodes.

## ADDED Requirements

### Requirement: The unlock table declares rules of AND-ed clauses and ownership grants

A rulebook table at `world/rules/rulebook/cross_lineage_unlock.yaml` SHALL declare an ordered list of rules. Each rule SHALL carry a unique non-empty `id`, a non-empty `requires` list of condition clauses, and a non-empty `grants` list of `SKILL_REGISTRY` keys. A rule SHALL be satisfied only when **every** clause in its `requires` list is satisfied (AND semantics). Rule `id` values SHALL be unique across the table and SHALL be independent of the keys granted, so one rule may grant several keys.

#### Scenario: A rule with all clauses satisfied grants every key it names

- **WHEN** an entity satisfies every clause of a rule whose `grants` names two keys the entity does not own
- **THEN** both keys are added to the entity's owned set

#### Scenario: A rule with one unsatisfied clause grants nothing

- **WHEN** an entity satisfies the first clause of a two-clause rule but not the second
- **THEN** no key from that rule's `grants` is added to the entity's owned set

#### Scenario: Duplicate rule ids fail at load

- **WHEN** the table declares two rules sharing an `id`
- **THEN** loading the table raises `ValueError` naming the duplicated `id`

### Requirement: A clause is satisfied by distinct qualifying groups

Each clause SHALL declare a `scope` selecting registry nodes, a `min_level` integer at least 1, and a `distinct_groups` integer at least 1 (defaulting to 1 when omitted). A `scope` SHALL select nodes either declaratively — by `category`, optionally narrowed by `group` — or by an explicit `keys` list of registry keys.

A declarative scope SHALL select `ACTIVE` nodes only: a `PASSIVE` member of the named category or group SHALL never be sampled, because practice accrues on use alone and a `PASSIVE` node therefore remains at level 0 forever. Selected nodes SHALL be partitioned into groups by their `group` field; a scope narrowed to a single `group`, and an explicit `keys` scope, SHALL form exactly one group.

A group SHALL qualify when at least one node in it has a derived proficiency level greater than or equal to `min_level`. A clause SHALL be satisfied when the number of qualifying groups is greater than or equal to `distinct_groups`.

#### Scenario: One node at the threshold qualifies its group

- **WHEN** a clause requires `distinct_groups` 1 at `min_level` 5, and the entity holds exactly one node in scope at proficiency level 5
- **THEN** the clause is satisfied

#### Scenario: Two nodes in the same group do not satisfy a two-group clause

- **WHEN** a clause requires `distinct_groups` 2 at `min_level` 5, and the entity holds two nodes at level 5 that belong to the same group
- **THEN** the clause is not satisfied

#### Scenario: Nodes in two different groups satisfy a two-group clause

- **WHEN** a clause requires `distinct_groups` 2 at `min_level` 5, and the entity holds one node at level 5 in each of two different groups
- **THEN** the clause is satisfied

#### Scenario: A node below the threshold does not qualify its group

- **WHEN** a clause requires `min_level` 5 and the entity's highest node in scope sits at level 4
- **THEN** the clause is not satisfied

### Requirement: The table fails closed on any rule that can never fire

Loading the table SHALL raise `ValueError` naming the offending rule `id` when a rule is unsatisfiable or malformed by construction, rather than admitting a rule that silently never fires. The load SHALL reject a rule when any of the following holds:

- a `grants` or `scope` entry names a key absent from `SKILL_REGISTRY`
- a clause's scope selects no nodes at all
- fewer of the clause's groups hold at least one sampled node whose derived proficiency cap is greater than or equal to `min_level` than the clause's `distinct_groups` demands
- an explicit `keys` scope names a node that is not `ACTIVE` — naming such a key is an authoring error, since it can never reach any threshold (a declarative scope instead never samples one, so it cannot fail this way)
- `min_level` or `distinct_groups` is not an integer of at least 1, or `grants`/`requires` is empty

#### Scenario: An unreachable threshold fails at load

- **WHEN** a clause declares `min_level` 5 over a scope whose every node has a derived proficiency cap of 3
- **THEN** loading raises `ValueError` naming the rule `id` and the unreachable threshold

#### Scenario: An explicit keys scope naming a PASSIVE node fails at load

- **WHEN** an explicit `keys` scope names a node whose kind is `PASSIVE`
- **THEN** loading raises `ValueError` naming the rule `id` and the offending key

#### Scenario: A declarative scope silently omits the category's PASSIVE members

- **WHEN** a declarative scope names a category that contains both `ACTIVE` and `PASSIVE` members
- **THEN** loading succeeds, and the clause's groups contain only the `ACTIVE` members

#### Scenario: A grant naming an unknown key fails at load

- **WHEN** a rule's `grants` names a key absent from `SKILL_REGISTRY`
- **THEN** loading raises `ValueError` naming the rule `id` and the unknown key

#### Scenario: A clause demanding more groups than can qualify fails at load

- **WHEN** a clause declares `distinct_groups` 3 over a scope containing only two groups that can reach `min_level`
- **THEN** loading raises `ValueError` naming the rule `id`

### Requirement: A granted key is never a condition source

No key named in any rule's `grants` SHALL appear in any rule's clause scope, including that of the granting rule itself. Loading SHALL raise `ValueError` naming both rule ids when this holds, so an unlock can never cascade into a further unlock.

#### Scenario: A grant feeding another rule's condition fails at load

- **WHEN** rule A grants a key that rule B's clause scope selects
- **THEN** loading raises `ValueError` naming both rule ids

#### Scenario: A grant feeding its own condition fails at load

- **WHEN** a rule's `grants` names a key its own clause scope selects
- **THEN** loading raises `ValueError` naming that rule id

### Requirement: Grants convey ownership only and are monotonic

A satisfied rule SHALL add its granted keys to the entity's stored owned skills and SHALL do nothing else. It SHALL NOT write practice proficiency for any key, so a granted node starts at proficiency level 0 and must be practised like any other. Granting SHALL be idempotent: a key the entity already owns, whether from an earlier grant, a character preset, or an import, SHALL be left untouched and SHALL NOT be duplicated in storage. No evaluation SHALL ever remove a key from the owned set.

#### Scenario: A granted node starts unpractised

- **WHEN** a rule grants a key the entity did not own
- **THEN** the entity owns that key and its derived proficiency level is 0

#### Scenario: Re-granting an already-owned key writes nothing

- **WHEN** a rule is satisfied again for an entity that already owns every key it grants
- **THEN** the entity's stored owned skills are unchanged and contain no duplicate entry

#### Scenario: A rule that stops being satisfied revokes nothing

- **WHEN** an entity that was granted a key by a rule is later evaluated under conditions that no longer satisfy that rule
- **THEN** the entity still owns the granted key

### Requirement: Evaluation runs on the practice-award path and nowhere else

Rule evaluation SHALL run immediately after practice proficiency is written, on every entry point that writes it, so the two practice paths cannot diverge. Evaluation SHALL NOT run on any read path: querying an entity's owned skills, previewing an action, or reading combat state SHALL produce no grant and no persistent write. Keys newly granted during an evaluation SHALL be announced through the same caller-owned sink that already carries newly-usable-skill lines.

#### Scenario: A practice award that crosses a threshold grants immediately

- **WHEN** a practice award raises a node's proficiency to a rule's `min_level` and that rule's remaining clauses are already satisfied
- **THEN** the rule's keys are granted within the same award and one announcement line per newly granted skill is appended to the caller's sink

#### Scenario: Reading owned skills grants nothing

- **WHEN** an entity that satisfies an unevaluated rule has its owned skills queried without any practice award
- **THEN** no key is granted and no persistent write occurs

#### Scenario: A practice award that changes no threshold grants nothing

- **WHEN** a practice award leaves every rule's satisfaction unchanged
- **THEN** no key is granted and the caller's sink receives no unlock line

### Requirement: The shipped table loads without violating any validation rule

Importing the cross-lineage unlock rulebook SHALL succeed: every rule the project ships SHALL pass every load-time validation rule stated above. A rule that is added or edited into a state that cannot fire SHALL break the import rather than ship dead, so the shipped table can never contain an unsatisfiable rule.

#### Scenario: The shipped rulebook imports cleanly

- **WHEN** the cross-lineage unlock rulebook is loaded
- **THEN** loading completes without raising, and every loaded rule declares at least one clause and at least one grant

#### Scenario: Editing a shipped rule into an unsatisfiable state breaks the load

- **WHEN** a rule is edited so that one of its clauses can never be satisfied
- **THEN** loading raises `ValueError` naming that rule id
