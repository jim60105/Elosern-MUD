# webclient-gallery-categories Specification

## Purpose
Define which subjects each category of the gallery window lists, how they are
grouped and ordered, and which subjects are admitted for gallery actions, so
every category is bounded by its own source and no kind can crowd out another.

## Requirements

### Requirement: The gallery has a closed, ordered category set
The gallery SHALL expose exactly the categories `mine`, `party`, `people`, `monster` and `scene`, in that order. Each category SHALL report its subject count, whether it is enabled, and a reason when it is disabled. Category building SHALL read only and write no state.

#### Scenario: Categories arrive in the fixed order
- **WHEN** the categories are built for any actor
- **THEN** their keys are exactly `mine`, `party`, `people`, `monster`, `scene` in that order

#### Scenario: Unreleased categories are disabled with a reason
- **WHEN** the categories are built with every source released
- **THEN** all five categories are enabled with a null reason

#### Scenario: Building reads only
- **WHEN** the categories and their groups are built twice for the same actor
- **THEN** both results are identical and no record, attribute or file changed

### Requirement: The mine category lists the owning account's characters
The `mine` category SHALL list every character of the account that owns the rendered puppet, in one unlabeled group: the live character first and marked current, then the others by numeric identity. While the puppet is a possessed companion, the owner is the companion's bound owner.

#### Scenario: The live character comes first
- **WHEN** an account owns synthetic characters with identities 5, 3 and 9 and character 9 is puppeted
- **THEN** `mine` lists 9 marked current, then 3, then 5, in one group without a label

#### Scenario: Possession keeps the account's characters
- **WHEN** the puppet is a companion possessed by the account's character 3
- **THEN** `mine` lists the account's characters with 3 marked current and does not list the companion

### Requirement: The party category lists the owner's live companions
The `party` category SHALL list, in one unlabeled group and in party order, the live companions of the owning character that have a gallery subject. While the puppet is a possessed companion, the owning character's party is listed.

#### Scenario: Party order is kept
- **WHEN** the owning character's party holds named companions B then A
- **THEN** `party` lists B then A

#### Scenario: A companion without a gallery subject is skipped alone
- **WHEN** one companion has no named portrait policy
- **THEN** it is not listed and the other companions are

### Requirement: The monster category lists sighted species by threat tier
The `monster` category SHALL hold one group per threat tier that has at least one registered visual species, in tier-registry order, the tier being that of the species' default variant. A group SHALL report `seen` and `total` and list only species whose `monster:<key>` entry is in the lore record the codex reads, in registry order.

#### Scenario: Unseen species get no subject
- **WHEN** a synthetic registry has species `t_a` and `t_b` in tier `t_low` and the holder has sighted only `t_a`
- **THEN** the `t_low` group lists only `t_a` with seen 1 and total 2

#### Scenario: An all-unseen tier still draws its group
- **WHEN** a second tier `t_high` has one registered species and none is sighted
- **THEN** a `t_high` group with seen 0, total 1 and no subjects follows the `t_low` group

### Requirement: Admission is membership of any enabled category
A subject SHALL be admitted for an actor exactly when it belongs to an enabled category for that actor, whichever category is currently selected. A subject in no enabled category SHALL NOT be admitted.

#### Scenario: A party companion is admitted while mine is selected
- **WHEN** the admission predicate is asked about a listed party companion's subject
- **THEN** it answers admitted

#### Scenario: An unsighted species is not admitted
- **WHEN** it is asked about a registered species the holder has not sighted
- **THEN** it answers not admitted

### Requirement: The people category lists met named NPCs grouped by place
The `people` category SHALL list every named NPC in the owning character's met-person record that exists now and is not in that character's party, never another player's character. It SHALL hold one group per place labelled with the place name, groups ordered by their most recent interaction and subjects inside a group by most recent interaction.

#### Scenario: Groups follow recency
- **WHEN** the record holds `t_npc_a` met at place P1 at sequence 3, `t_npc_b` at P2 at sequence 5 and `t_npc_c` at P1 at sequence 4
- **THEN** the groups are P2 (`t_npc_b`) then P1 (`t_npc_c`, `t_npc_a`)

#### Scenario: Party members are listed only under party
- **WHEN** `t_npc_b` joins the owning character's party
- **THEN** `people` no longer lists it and `party` does

#### Scenario: A vanished NPC is not listed
- **WHEN** a recorded NPC no longer exists
- **THEN** no group lists it and an emptied place has no group

#### Scenario: Possession lists the owner's people
- **WHEN** the puppet is a companion possessed by character C
- **THEN** `people` lists C's met people

### Requirement: The scene category lists entered archetypes
The `scene` category SHALL list, in one unlabeled group and in registry order, the scene archetypes recorded in the owning character's scene-entry record that are still registered, each as its scene subject named by the archetype's display name.

#### Scenario: Only entered archetypes are listed
- **WHEN** the synthetic registry declares `t_arch`, `t_other` and `t_third` and the owner has entered `t_third` and `t_arch`
- **THEN** `scene` lists `t_arch` then `t_third` in one group without a label

#### Scenario: Nothing entered lists nothing
- **WHEN** the owner has entered no archetype
- **THEN** `scene` is enabled with count zero and no subject
