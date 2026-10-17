# Spec Delta

## ADDED Requirements

### Requirement: Party combat command references document actor scope drafts and exit confirmations
Both player command documents SHALL describe combat command skill/item/tactic syntax, combat actions actor discovery, cast/use draft routing, automatic final selection, revisions and explicit party retreat/surrender confirmation with session/round-bound token. Keys, aliases and contexts SHALL match the mounted commands and curated manifest.

#### Scenario: Documented runnable syntax
- **WHEN** the reference lists combat command a2 skill skill_key@scale=targets, item item_key=target or defend/dodge/taunt forms
- **THEN** each form maps to the mounted parser and actor-local server validation, and no separate whole-party submit is documented

#### Scenario: Explicit exit text
- **WHEN** a text player invokes combat retreat, combat forfeit or an allied flee/surrender alias
- **THEN** a party consequence prompt requires confirm plus its token, other continuations cancel, and no documented command bypasses that confirmation

