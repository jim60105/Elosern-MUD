## MODIFIED Requirements

### Requirement: The gallery has a closed, ordered category set
The gallery SHALL expose exactly the categories `mine`, `party`, `people`, `monster` and `scene`, in that order. Each category SHALL report its subject count, whether it is enabled, and a reason when it is disabled. Category building SHALL read only and write no state.

#### Scenario: Categories arrive in the fixed order
- **WHEN** the categories are built for any actor
- **THEN** their keys are exactly `mine`, `party`, `people`, `monster`, `scene` in that order

#### Scenario: Unreleased categories are disabled with a reason
- **WHEN** the categories are built while the scene source is not released
- **THEN** `scene` is disabled with a non-empty reason and a count of zero, and the other four are enabled with a null reason

#### Scenario: Building reads only
- **WHEN** the categories and their groups are built twice for the same actor
- **THEN** both results are identical and no record, attribute or file changed

## ADDED Requirements

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
