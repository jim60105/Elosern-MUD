# Proposal: expose-stat-breakdown-read-model

## Why

After P2–P5 the player's numbers quietly change under the hood — equipment
flats, skill multipliers, condition rules, Church graces — but every surface
still shows only a single opaque number, and the character panel cannot
explain WHY a value moved. This is P6 of the equipment-effects design
(parent design §11): one server-side breakdown read model that decomposes
each stat into `base → effective` with named layers per source
(skill／condition／equipment), the exact §6 formula shared with combat so
the panel and settlement can never disagree, and the character panel
payload bumped to v5 carrying those layers. The Vue renderer is P7.

## What Changes

- New capability `character-breakdown-view`: `world/rules/status_query.py`
  gains a breakdown read model — for each panel stat, `base` (stored
  literal, never baked), ordered `layers` of `{source:
  skill|equipment|condition, name, kind: mult|flat|pct, amount}` (skill
  layers from owned `StatMultiplyEffect`s named by skill registry label;
  condition layers from matched rule/buff adjustments named by the shipped
  `STATUS_DISPLAY` labels; equipment layers per worn item named by
  `display_name_zh`, gauge caps rendered as flat layers on the gauge
  maximum), and `effective` composed FROM those layers using each stat's
  named authoritative shipped computation (explicit parity mapping with
  documented exceptions: initiative's raw-agility, consumer post-effective
  floors — no blanket-equality claim).
- Character panel payload becomes schema version 5: trait rows become
  `{key, label, base, current, max, effective, layers}` — `current` stays
  the total-display field on EVERY row (statics equal `effective`; gauges
  carry the resource remainder, their `max` decomposed into layers with
  equipment caps as equipment flat layers); `effective` composes from the
  layers via each stat's named authoritative computation (explicit
  mapping + documented exceptions — initiative's raw agility, consumer
  post-floors — per change design D1); equipment rows gain the
  server-formatted `adjustment` text (P3 formatter); every other section
  keeps its v4 shape. Accounting-incomplete or over-bound breakdowns fail
  closed into the common unavailable form — never silent skips.
- Text client parity: the text status/inventory views print the same layer
  rows and adjustment summaries; the compact combat status surface keeps
  showing effective totals only (breakdown is the character panel's job).
- Transitional browser tolerance: the legacy JS client accepts schema
  version 4 and 5 via version-dispatched exact-shape validators (both
  sides), rendering `current`/`max` exactly as today (statics included);
  P7 renders breakdowns and drops 4. No command key/alias/syntax change
  (`tests/test_command_docs.py` green).

No backward compatibility or migration work (the v5 payload simply ships;
no persisted payload data exists).

## Capabilities

### New Capabilities

- `character-breakdown-view`: the breakdown read model, the single shared
  effective-value formula helper, the text-client layer rendering, and the
  compact surface totals-only contract.

### Modified Capabilities

- `webclient-exploration-menu`: the character panel requirement moves from
  an exact version-4 payload to an exact version-5 payload with
  `base`/`effective`/`layers` trait rows, gauge maximum decomposition, and
  equipment `adjustment` rows.

## Impact

- `world/rules/status_query.py`: breakdown rows + pure layer-then-value
  builder over no-create snapshot reads; existing strict validators
  extended to the new shape.
- `web/webclient/presentation/character.py`: `CHARACTER_SCHEMA_VERSION = 5`,
  row shape changes, equipment adjustment text; Python panel validator
  dispatches v4 (test fixtures only) vs v5 (production).
- Text client: `commands/` status/inventory view formatting (payload text
  only; no keys/aliases/syntax change).
- `web/static/webclient/js/elosern/protocol.js` (+ legacy fixtures/tests):
  version-dispatched exact-shape validation accepting 4 and 5, totals
  rendering unchanged.
- Tests: breakdown layer composition and accounting-completeness
  fail-closed, purity byte-identical build, per-stat parity against the
  named authoritative computations, gauge max decomposition (incl. P2 sync
  + P5 grace rules), adjustment text on panel rows, text-client snapshots,
  legacy-client v4/v5 branch tests, full panel contract validators at v5,
  `npm test` green.
- Not affected: combat math, payloads' consumers other than the character
  panel, saved state (none), Vue components (P7).
