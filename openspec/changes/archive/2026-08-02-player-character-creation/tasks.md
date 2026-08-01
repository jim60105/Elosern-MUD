## 1. Lore-backed starting profiles

- [x] 1.1 Extend `RaceProfile` and `RACE_REGISTRY` with immutable,
  cap-safe `starting_magic_level` values, and update lore-registry tests.
- [x] 1.2 Add a frozen `PlayerPreset` catalog with at least one adult,
  allocation-valid preset per selectable race.
- [x] 1.3 Implement and unit-test the pure player starting-profile resolver for
  race/subrace vital bands, static modifiers, six-axis spans, and the exact
  finite allocation budget.

## 2. Deterministic character activation

- [x] 2.1 Add typed creation requests/results and deterministic preflight for
  ownership, pending state, adult fields, race/subrace compatibility, presets,
  display name, and allocation constraints.
- [x] 2.2 Implement the transactional activation service in `world.rules`,
  including strict integer-band validation of one injected magic-level sample,
  initialization of every creation-owned mechanical surface, and full rollback
  of trait cache and persistent attributes on every write failure.
- [x] 2.3 Add persistent player-character identity and creation-state fields;
  retain the existing deterministic race-baseline contract while applying
  validated player values only during activation.

## 3. Registration and command flow

- [x] 3.1 Mark every Evennia auto-created account character as pending through
  an account creation hook that preserves the parent ownership setup, and
  derive a `Replace`/`no_exits`/`no_objs` creation-only gate from that state
  across reconnects and reloads.
- [x] 3.2 Implement the `character` preset selector and custom creation wizard,
  including confirmation, cancellation, input feedback, and activation
  messaging.
- [x] 3.3 Restore the normal character command set only after a successful
  activation, without creating a second character object or changing account
  ownership.

## 4. Regression coverage and player documentation

- [x] 4.1 Add focused pure-logic tests for profile bounds, exact-budget
  rejection, subrace ordering, magic endpoint rolls, invalid rolls, and
  no-reroll-on-rejection behavior.
- [x] 4.2 Add Evennia integration tests for registration, parent ownership,
  pending command gating including exits and objects, reconnect/reload
  persistence, both creation modes, name and age gates, unchanged shell
  placement, successful `rest`, and fault-injected atomic rollback.
- [x] 4.3 Update player-facing connection and character documentation with the
  two creation modes, required adult identity fields, allocation rule, and
  supported first commands.

## 5. Verification

- [x] 5.1 Run the focused creation, trait, progression, and command test
  modules with `uv run --locked evennia test --settings settings.py`.
- [x] 5.2 Run `uv run --locked evennia test --settings settings.py .`,
  `uv run --locked python -m compileall -q world typeclasses commands server`,
  `openspec validate player-character-creation --strict`, and `git diff --check`.
