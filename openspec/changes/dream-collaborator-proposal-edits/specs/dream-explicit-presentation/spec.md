# Spec Delta

## MODIFIED Requirements

### Requirement: Collaborator has separate spoiler-filtered capability access

The collaborator SHALL receive the player's current message, the current dream proposal with line numbers, the chosen thread's player-visible label when one is chosen, creative preferences and a spoiler-filtered adventure summary. It SHALL receive no transcript of earlier exchanges and SHALL exclude StoryDirector hidden answers, system fields and other owners private cognition. The guardrail SHALL reject leaked metadata/spoilers and claimed authoritative mutations while permitting explicit scene prose. A shared deployment profile SHALL NOT share capability history or permissions.

#### Scenario: Hidden director context exists
- **WHEN** StoryDirector has a secret solution for the same thread
- **THEN** collaborator context excludes it and a response attempting to disclose forbidden metadata rejects

#### Scenario: Current proposal enters the prompt with line numbers
- **WHEN** a prompt is built for a proposal that holds a summary and two list items in one field
- **THEN** the request carries every proposal field, each line paired with its line number starting at one, and the closed edit vocabulary

#### Scenario: Chosen thread label enters the prompt
- **WHEN** a prompt is built with a chosen thread label, and again with none
- **THEN** the first request carries that label and the second carries no thread entry

#### Scenario: No transcript
- **WHEN** a prompt is built for a later exchange of a session
- **THEN** the request's context keys are exactly the permitted set and none of them carries an earlier message, scene or line

## ADDED Requirements

### Requirement: Collaborator responses carry proposal edits validated by application

A response SHALL be able to carry an ordered set of proposal edit commands. The set SHALL be validated by applying it to the proposal the prompt carried; a set that does not apply SHALL invalidate the whole response and go through the existing validation retry. Edit text SHALL pass the same forbidden-content validators as scene and dialogue. An accepted response SHALL yield the resulting proposal and its change report; the layer itself SHALL write no state.

#### Scenario: Valid edits yield the new proposal and report
- **WHEN** a response edits two fields of the supplied proposal with commands that apply
- **THEN** the accepted exchange carries the proposal after those edits and a change report naming exactly those changes

#### Scenario: No edits
- **WHEN** a response carries an empty edit set or none
- **THEN** it is accepted, the resulting proposal equals the supplied one and the report shows no change

#### Scenario: Invalid edits retry
- **WHEN** the first response's edit set does not apply and the retried response's set does
- **THEN** exactly one exchange is accepted, built from the retried response

#### Scenario: Retries exhausted
- **WHEN** every attempt returns an edit set that does not apply
- **THEN** the call degrades to the unavailable result and no proposal is produced

#### Scenario: Forbidden content inside an edit
- **WHEN** an edit's new text contains a forbidden metadata, state-change or divine-identity marker while scene and dialogue are clean
- **THEN** validation rejects the response

#### Scenario: Legacy requirement list is refused
- **WHEN** a response carries a whole requirement list field instead of edits
- **THEN** the output schema rejects it
