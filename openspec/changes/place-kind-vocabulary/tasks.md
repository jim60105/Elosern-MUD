## 1. The vocabulary

- [ ] 1.1 Extend `PlaceKind` in `world/lore/settlements/places.py` with `JEWELLER`,
  `ALCHEMIST`, `TEMPLE`, `SANCTUM_SHOP`, `TAVERN`, `LODGING`, `BATHHOUSE`, `PALACE`,
  `WATCH_POST`, `TRAINING_GROUND`, `ACADEMY`, `MERCHANT_HALL`, `MARKET`, `COMMONS`.
- [ ] 1.2 Document on the enum what a kind means: the location, never the host's capability,
  and never a runtime lens. Point at the elven homes as the worked example — they are `HOME`
  although each one trades.
- [ ] 1.3 Change no shipped row's kind.

## 2. The rule

- [ ] 2.1 Add the kind rule to the place-record requirement in
  `settlement-place-registry`.
- [ ] 2.2 Cover it: a synthetic place whose room is a dwelling and whose host trades is
  authored as a home, and the shipped rows each carry a kind that matches what their room is.
- [ ] 2.3 Confirm by grep that `kind` still has no reader outside the registry modules, and
  record the result. If one has appeared since, it needs discussing before this lands.

## 3. Handoff

- [ ] 3.1 Run the lore settlements and guild-config suites plus
  `uv run --locked python -m tools.spec_traceability check`.
