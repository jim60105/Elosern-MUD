## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: The scene category lists entered archetypes
The `scene` category SHALL list, in one unlabeled group and in registry order, the scene archetypes recorded in the owning character's scene-entry record that are still registered, each as its scene subject named by the archetype's display name.

#### Scenario: Only entered archetypes are listed
- **WHEN** the synthetic registry declares `t_arch`, `t_other` and `t_third` and the owner has entered `t_third` and `t_arch`
- **THEN** `scene` lists `t_arch` then `t_third` in one group without a label

#### Scenario: Nothing entered lists nothing
- **WHEN** the owner has entered no archetype
- **THEN** `scene` is enabled with count zero and no subject
