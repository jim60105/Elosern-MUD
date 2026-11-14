# Spec Delta

## Purpose

Defines the two player entry points of a landmark rite, the browser action and the text command, which share one settlement and one set of refusal codes.

## ADDED Requirements

### Requirement: The rite action accepts only an option and a performer
The rite action SHALL accept exactly an option key and a nullable party member identifier, and SHALL reject any other payload before reaching the settlement. The district, archetype, cost and scene SHALL never be taken from the request.

#### Scenario: Exact payload
- **WHEN** a request carries a well-formed option key and a null member identifier
- **THEN** it is accepted and settles the controlled character's rite at the current landmark

#### Scenario: Malformed payload
- **WHEN** a request carries an extra field, a missing field, a malformed option key, or a boolean or negative member identifier
- **THEN** it is rejected and nothing is settled

### Requirement: A successful rite action returns the delivered scene
A successful rite action SHALL return the committed rite's scene as an authored-scene delivery with a delivery identity unique to that committed rite, the names of the acting body and the guardian, and the scene's lines in authored order, together with whether this was the district's first completion.

#### Scenario: Controlled character
- **WHEN** the controlled character completes a synthetic rite
- **THEN** the result carries the self scene's lines in order, the second-person actor name and the guardian's name

#### Scenario: Companion
- **WHEN** a companion completes an option that declares a watch scene
- **THEN** the result carries the watch scene's lines with the companion-name placeholder replaced by the companion's name, and the companion's name as the actor name

### Requirement: Rite action refusals are stable and a duplicate request settles once
A refused rite action SHALL return a rejected outcome carrying the settlement's stable refusal code and SHALL change nothing. Two requests with the same request identity SHALL settle once and return the same delivery.

#### Scenario: Refusal
- **WHEN** the action is requested away from a landmark, or with an option the landmark does not offer
- **THEN** each returns a rejected outcome with its own code and time, sexual state and the record are unchanged

#### Scenario: Duplicate
- **WHEN** one request identity is dispatched twice
- **THEN** world time advanced once and both results carry the same delivery identity

### Requirement: The rite command lists and performs rites from the text client
The rite command SHALL, with no argument, list the landmark's guardian, its options and which were experienced without changing anything; with an option, perform it with the controlled character; and with an option and a companion name, perform it with that companion. It SHALL emit the complete scene in order and then one completion line.

#### Scenario: Listing
- **WHEN** the command is entered with no argument on a synthetic landmark before and after one completion
- **THEN** both listings name the guardian and both options, only the second marks the completed option as experienced, and neither changes time or the record

#### Scenario: Perform by key or label
- **WHEN** the command is entered with an option's key, or with its label
- **THEN** the rite settles and the whole scene is emitted before the completion line

#### Scenario: Companion and refusals
- **WHEN** the command names a present companion, an unknown companion, an unknown option, or is entered away from a landmark
- **THEN** the first settles with the companion and the others each emit the settlement's refusal message and change nothing
