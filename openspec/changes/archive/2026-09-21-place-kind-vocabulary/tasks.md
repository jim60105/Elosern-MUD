## 1. The vocabulary

- [x] 1.1 Extend `PlaceKind` in `world/lore/settlements/places.py` with `JEWELLER`,
  `ALCHEMIST`, `TEMPLE`, `SANCTUM_SHOP`, `TAVERN`, `LODGING`, `BATHHOUSE`, `PALACE`,
  `WATCH_POST`, `TRAINING_GROUND`, `ACADEMY`, `MERCHANT_HALL`, `MARKET`, `COMMONS`.
- [x] 1.2 Document on the enum what a kind means: the location, never the host's capability,
  and never a runtime lens. Point at the elven homes as the worked example — they are `HOME`
  although each one trades.
- [x] 1.3 Change no shipped row's kind. Confirmed by the shipped-kind pin test: all nine
  shipped rows carry exactly the kinds they shipped with.

## 2. The rule

- [x] 2.1 Add the kind rule to the place-record requirement in
  `settlement-place-registry`.
- [x] 2.2 Cover it: a synthetic place whose room is a dwelling and whose host trades is
  authored as a home, and the shipped rows each carry a kind that matches what their room is.
  Also pinned: the closed twenty-member value set with snake_case wire values (sync mirrors
  the value, so a member authored without one would write the uppercase name to the DB).
- [x] 2.3 Confirm by grep that `kind` still has no reader outside the registry modules, and
  record the result. If one has appeared since, it needs discussing before this lands.
  Grepped. One reader exists outside `world/lore/settlements/`:
  `web/browser_support/browser_fixtures_data/probes.py::live_place_by_kind` compares
  `place.kind == kind` to pick a browser-fixture interior (callers pass `"guild_hall"` /
  `"general_store"`). It is test-support fixture selection, not a game mechanism: it looks
  up a row by an existing member's value, never gates behaviour on the vocabulary, and it
  predated this change (landed with the browser-fixture split on 2026-09-20). Nothing under
  `world/rules/`, `world/maps/` or `commands/` reads `kind`. Discussed and accepted as
  benign: it is exactly the "whoever eventually reads it" the design anticipated, and this
  change adds no member it could mis-select on.

## 3. Handoff

- [x] 3.1 Run the lore settlements and guild-config suites plus
  `uv run --locked python -m tools.spec_traceability check`.
  `world.lore.tests.test_settlements` 24/24 green (three new covering tests);
  `world.rules.tests.test_guild_config` green; `tools.spec_traceability check` green.
