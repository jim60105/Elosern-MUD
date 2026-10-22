# Spec Delta

## ADDED Requirements

### Requirement: Recent deeds are selectable from their own committed settlement

A supported recent-deed occurrence SHALL be selectable through the composition root from its own committed settlement, without evidence created around the settlement boundary. A validated response SHALL cite only IDs rendered for that request.

#### Scenario: Real accomplishment reaches the request
- **WHEN** a synthetic non-title-bearing achievement is settled through its actual owner and the nomination workflow receives the committed trigger
- **THEN** the rendered request cites that occurrence and the validated five-candidate response persists a ballot

#### Scenario: Real adult action reaches the request
- **WHEN** an adult action is settled through its real resolver with an untouched recipient control
- **THEN** only authorized actor and recipient outcomes reach the request, while the control retains unchanged gameplay and no unauthorized fields appear

### Requirement: Committed nomination state survives reload

A committed ballot, title grant and award result SHALL remain readable through a fresh production instance after cache eviction.

#### Scenario: Fresh instance reads committed results
- **WHEN** a nomination ballot and its title grants commit, then object and attribute caches are evicted
- **THEN** a freshly loaded production instance returns the same stored ballot and grant results
