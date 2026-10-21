# Spec Delta

## ADDED Requirements

### Requirement: Step 7 selects narration without changing what resolution decides

When step 7 builds the event log it SHALL select each entry's authored narration line before
the log is handed to the event-effect planners. Narration SHALL NOT roll dice, recompute a hit
or an amount, reorder or add entries (except the single action-narration entry for an
otherwise-empty successful log), mutate any state, or reject the action. Entry kinds, entry
order and every entry's numeric data SHALL match the pre-narration result.

#### Scenario: Resolving twice produces the same decisions and different prose only by scope

- **WHEN** the same request is resolved twice with the gameplay dice patched to a fixed
  sequence
- **THEN** both results carry identical entry kinds, order and numeric data, and identical hit
  and damage draw counts

#### Scenario: A narration lookup miss never rejects the action

- **WHEN** step 7 builds a log for a skill key the narration catalog does not know
- **THEN** the action still returns a successful result carrying a fallback line for every
  entry, and no named rejection reason is produced

#### Scenario: Planners still see the immutable log

- **WHEN** step 7 completes narration
- **THEN** every registered event-effect planner still receives the same entry kinds, order
  and data it received before narration existed

### Requirement: Narration scope is supplied through the action context

The action context's event context SHALL be able to carry an optional narration scope, and the
combat round and out-of-combat cast paths SHALL supply one derived from already-known
deterministic identifiers (session or field identity, round index, action ordinal, world
tick). A request that supplies no scope SHALL still resolve and narrate.

#### Scenario: A round supplies a stable scope

- **WHEN** an ordinary combat round resolves two actions of the same skill against the same
  target
- **THEN** each action's narration scope differs, and re-resolving the same round record's
  inputs reproduces the same scopes

#### Scenario: Casting outside combat needs no new plumbing

- **WHEN** a skill is cast with a context that carries no narration scope
- **THEN** the cast succeeds and each entry renders a catalog line selected from the remaining
  seed inputs
