# Spec Delta

## ADDED Requirements

### Requirement: Every non-elemental ACTIVE skill has its own action narration

Each ACTIVE skill in the martial-arts, holy-rite, divine-mystery and enhancement categories
SHALL declare its own authored action narration, and SHALL render that line as the opening of
its resolved action instead of the category-tier line. The catalog's pending-family set SHALL
no longer contain those four categories.

#### Scenario: Two skills of one family open differently

- **WHEN** two ACTIVE martial-arts skills resolve against the same target under the same
  narration scope
- **THEN** each log's opening line comes from that skill's own row and the two lines differ

#### Scenario: A newly added skill in these families fails at import without a row

- **WHEN** an ACTIVE martial-arts, holy-rite, divine-mystery or enhancement skill exists in the
  shipped registry with no authored narration row
- **THEN** catalog loading raises a named narration-catalog error naming that skill

#### Scenario: The authored rows still obey the shared bounds

- **WHEN** a family row exceeds the literal-length budget, the slot budget or the no-digit rule
- **THEN** catalog loading raises the same named error the bound contract defines, with no
  family-specific exception
