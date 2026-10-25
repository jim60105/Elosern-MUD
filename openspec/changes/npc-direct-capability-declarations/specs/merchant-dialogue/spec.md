# Spec Delta

## MODIFIED Requirements

### Requirement: Every merchant host answers when spoken to
A merchant service host SHALL carry a dialogue capability alongside its trade capability, and
every merchant place SHALL author the dialogue table its host answers from. A merchant place
that authors no dialogue key SHALL fail load naming the place: a shopkeeper who cannot be
spoken to is the defect this rule removes, so an unauthored table is an authoring error rather
than a silent default.

#### Scenario: Talking to a shopkeeper gets an answer
- **WHEN** a player talks to a merchant host
- **THEN** its authored greeting is returned, and its authored keywords answer

#### Scenario: A merchant place without a dialogue key fails load
- **WHEN** a synthetic merchant place authoring no dialogue key is loaded
- **THEN** validation raises naming the place and the missing identity kwarg

#### Scenario: Trade is unaffected by the added capability
- **WHEN** stock is listed and goods are bought and sold from a merchant host
- **THEN** the results are identical to before the dialogue capability was added

#### Scenario: Direct authoring preserves merchant speech
- **WHEN** shipped merchant rows are converted to direct components
- **THEN** each retains its existing scripted dialogue without blueprint expansion
