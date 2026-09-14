## ADDED Requirements

### Requirement: A conditional follow-up strike repeats damage without repeating the action
A validated damage policy SHALL permit one extra independent strike against a target with matching recent evidence. Each strike SHALL have an independent hit roll and the same coefficient/policy. The first miss SHALL NOT suppress the second strike. The action SHALL pay resources/time and award eligible practice once, project ordered damage correctly, and retain both rolls while emitting at most one terminal defeat or knockout for a target.

#### Scenario: A first miss does not suppress the second roll
- **WHEN** fixed rolls make the first strike miss and the follow-up hit on an eligible target
- **THEN** only the second damages HP and both rolls are recorded for one paid cast

#### Scenario: Ineligible target has one strike
- **WHEN** recent evidence is missing or expired
- **THEN** only the ordinary strike occurs

#### Scenario: Repeated damage is atomic and nonlethal aware
- **WHEN** two strikes cross a protected target or a later commit step fails
- **THEN** successful settlement floors HP at 1 with one knockout; a failed settlement restores all HP and evidence
