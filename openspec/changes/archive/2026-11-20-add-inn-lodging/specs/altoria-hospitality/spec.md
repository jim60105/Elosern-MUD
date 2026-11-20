# Spec Delta

## MODIFIED Requirements

### Requirement: A hospitality location adds no mechanism it does not have
The capital inn SHALL offer paid lodging through its existing host and authored lobby as defined by `inn-lodging`. The tavern and bathhouse SHALL NOT introduce drink, gambling, or bathing effects, charges, or persisted fields. All three places SHALL follow `city-sleep-policy`; awake rest, practice, conversation, and party invitation retain their existing rules.

#### Scenario: No new command or persisted state arrives with the rooms
- **WHEN** the player requests lodging from each of the three hospitality hosts
- **THEN** only the inn can quote and confirm lodging; the tavern and bathhouse add no command and create no lodging state

#### Scenario: Resting in the inn is resting anywhere
- **WHEN** the player rests awake or practises in a hospitality interior
- **THEN** the same awake settlement and cost apply as elsewhere without a hospitality charge or effect
