# Delta Specs: Stale Skip-Safety Assertions and Art-Portrait Focus Race

## ADDED Requirements

### Requirement: Registry-content assertions use the registry's key domain

Any test asserting membership or contents of a process-global registry covered
by the isolation contract SHALL use that registry's documented key domain, not
an incidental attribute of the entities it indexes. The skip-safety battlefield
registry SHALL be asserted with participant dbrefs: a test that checks
`world.rules.skip_safety._BATTLEFIELDS` SHALL assert `str(entity.pk)` keys,
never `str(entity.key)` display keys, matching the dbref indexing the registry
implements.

#### Scenario: Restore path registers each participant by dbref

- **WHEN** a persisted combat session is restored and the test verifies the
  skip-safety registration survived
- **THEN** the test asserts `str(actor.pk)` and `str(monster.pk)` are present in
  `_BATTLEFIELDS` after restoration, never the participants' display keys

#### Scenario: Display-key assertion fails under the dbref-keyed registry

- **WHEN** a test asserts that a participant's display key is a key of
  `_BATTLEFIELDS` whose entries are indexed by participant dbref
- **THEN** the assertion fails, proving the display-key form is not the
  registry's key domain
