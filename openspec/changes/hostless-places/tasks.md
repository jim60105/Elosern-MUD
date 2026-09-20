## 1. The optional host

- [ ] 1.1 In `world/lore/settlements/places.py`, give **every field from `host_name`
  onwards** a default, in declaration order: `host_name`, `host_title`, `host_race`,
  `host_subrace`, `host_sex`, `profession`, `service_id` default to `None`;
  `assortment_keys` and `authored_kwargs` default to `()`.
  `assortment_keys` is easy to miss and is the one that breaks the build: it sits between
  `service_id` and `authored_kwargs` (places.py:54), so defaulting the host fields without it
  raises `TypeError: non-default argument 'assortment_keys' follows default argument` when the
  module is imported. `authored_kwargs` defaults to `()` rather than `None` so the shop-key
  scan in `guild_config.py`, which calls `dict(place.authored_kwargs)` unconditionally, keeps
  working against a host-less row without a guard.
  `host_subrace` does **not** have a default today — every shipped row passes it explicitly —
  so it needs one added like the rest, and it stays outside the all-or-nothing set below
  because `None` is a legitimate authored value for it.
- [ ] 1.2 In `validate_place_registry`, add the all-or-nothing check over those seven fields.
  The error names the place, the fields found and the fields missing; that message is the point
  of the rule, so assert on its content, not just that it raises.
- [ ] 1.3 Extend the existing goods rule: a place authoring no host SHALL declare no
  `assortment_keys`, no `extra_item_keys` and no `excluded_item_keys`. Fold it into the block
  that already enforces assortments-iff-shop-identity rather than adding a second loop.
- [ ] 1.4 Keep the existing per-field validation reachable only when the host is authored —
  an absent `host_race` must not be reported as "unknown race `None`".

## 2. The roster skips them

- [ ] 2.1 In `validate_service_hosts`, skip a place that authors no host. State it positively
  at the top of the loop so the function still reads as one row per host-declaring place.
- [ ] 2.2 Confirm by reading that no other consumer of `PLACE_REGISTRY` assumes a host:
  `world/maps/bootstrap.py` reads only room and doorway fields, and `_place_for_shop` reads
  `authored_kwargs`. Neither needs an edit; record in the task that this was checked rather
  than assumed.

## 3. Coverage

- [ ] 3.1 Add a host-less place to the synthetic test-data kit, beside the existing synthetic
  place rows, so downstream changes have a fixture to build on.
- [ ] 3.2 Cover over synthetic rows: a host-less place loads and derives no roster row; a
  half-authored host fails naming the broken fields; a host-less place declaring goods fails.
- [ ] 3.3 Cover the sync side over a synthetic host-less place: the interior exists once,
  tagged and described, with both doorways, and no NPC stands in it — and a second run creates
  nothing new.

## 4. Prove nothing shipped moved

- [ ] 4.1 Assert all nine shipped places still author complete hosts and the derived roster is
  field-for-field what it was. The capability ships unused.
- [ ] 4.2 Run the lore settlements, guild-config and guild-economy-sync suites, plus
  `uv run --locked python -m tools.spec_traceability check`.
