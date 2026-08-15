## ADDED Requirements

### Requirement: The no-create status read model resolves the derived arousal level from stored pleasure, not a raw arousal key
`world/rules/status_query.py::_sexual_condition_context()` SHALL resolve its `"arousal"` context
entry from the persisted `pleasure` counter's stored value (via the same band lookup
`SexualState.arousal` uses at read time), for any entity whose `sexual_traits` handler has been
materialized, rather than from a raw `"arousal"` key — which SHALL NOT exist in that storage once an
entity's `SexualState` has been built. For an entity whose handler has never been materialized, this
path SHALL still read `"arousal"` as a level string from the entity's frozen import-time baseline
Attribute, exactly as before this capability's amendment — preserving "Unmaterialized sexual baseline
remains unmaterialized" without modification. This resolution SHALL NOT read `entity.sexual`,
construct a `TraitHandler`, or otherwise materialize any persistent state, matching "Status
presentation has no mutation side effects"'s existing no-create discipline.

This requirement exists so that "Sexual threshold appears only while matched"'s existing, unmodified
scenario — the sexual condition entry appears and disappears as the actor's *canonical* arousal state
crosses and re-crosses the configured threshold — continues to hold true once `pleasure` (not a
directly-stored `arousal` level) is the canonical quantity: without this resolution, a materialized
entity's status entry would freeze at its import-time baseline and stop tracking canonical state
entirely, silently violating that scenario.

#### Scenario: The status panel reflects live pleasure on a materialized entity
- **WHEN** an entity's `SexualState` has been materialized and its `pleasure` has since been raised at
  runtime past the `高度` band's floor, and a status payload is built for that entity without first
  reading `entity.sexual` directly
- **THEN** the status payload's `conditions` include the `high_arousal_agility_accuracy_penalty`
  entry with its Traditional Chinese label and exact `agility`/`accuracy` adjustments

#### Scenario: The status panel's sexual entry disappears again as canonical state changes
- **WHEN** a status payload is built for a materialized entity whose `pleasure` is within the `高度`
  band (condition present), `pleasure` is then reduced below that band's floor by any canonical path,
  and a second status payload is built
- **THEN** the second payload's `conditions` no longer include the sexual-threshold entry — matching
  the shipped "Sexual threshold appears only while matched" scenario's existing "disappears after
  canonical state no longer matches" behaviour, now driven by `pleasure` rather than a directly-stored
  `arousal` level

#### Scenario: An unmaterialized entity's status still resolves from its import baseline, and remains unmaterialized
- **WHEN** a valid actor has import-time baseline sexual data but no materialized `sexual_traits`
  handler, and a status payload is built
- **THEN** the resolved arousal-driven presentation state matches the baseline's `arousal` level
  string, and no `sexual_traits` Attribute is created as a result of building status
