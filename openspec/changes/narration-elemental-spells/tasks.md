# Tasks

## 1. Fire, water, wind, earth

- [ ] 1.1 Author `world/skills/narration/data_fire.py` (every ACTIVE fire spell, one or two
  variants, the fire register) and verify the validator accepts it and two fire spells select
  different openings.
- [ ] 1.2 Author `world/skills/narration/data_water.py` and `data_wind.py` the same way, adding
  the area-spell override where the spell addresses the field; verify each two-spell pair
  differs.
- [ ] 1.3 Author `world/skills/narration/data_earth.py`, including its area and control spells;
  verify the validator accepts the module and the area opening is rendered once for a
  multi-target cast.

## 2. Lightning, ice, light, dark

- [ ] 2.1 Author `world/skills/narration/data_lightning.py` and `data_ice.py`; verify each
  two-spell pair differs and no row uses the fire or water register.
- [ ] 2.2 Author `world/skills/narration/data_light.py`, keeping its wording distinct from the
  holy-rite family's liturgical register; verify a light spell and a holy rite never share a
  line.
- [ ] 2.3 Author `world/skills/narration/data_dark.py`; verify the validator accepts it and the
  dark register's lines carry no digit and no gore.

## 3. Close the family and verify

- [ ] 3.1 Import the eight modules in the catalog aggregate and remove elemental magic from the
  frozen pending-family set; verify import fails when one spell's row is deleted and the
  pinning test names sexual acts as the only pending family.
- [ ] 3.2 Extend the coverage-contract slice to assert exact key-set equality for all eight
  elements plus the cross-element distinctness check, then run the focused catalog, selection
  and pipeline modules and the traceability check; verify every assertion in this delta has a
  matching annotated test.

## Workflow follow-up

- Archive the change after review and merge, syncing the added requirement into the
  `action-narration` main spec.
