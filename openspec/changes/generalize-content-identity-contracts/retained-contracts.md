# WP1 retained-contract assertion disposition (task 1.3)

Baseline `master` = `fbfd20ab8755a44cf4fc3d12362a70d345d912f0`. Every id below is read from the current specs with
`uv run --locked python -m tools.spec_traceability list`.

This file names what must **not** migrate. Preparing the deltas for the selected families does not
move data ownership, ids or assertions for any requirement listed here; the corresponding tests keep
their ids, their `Data-contract test:` reasons and their assertions. A later package that needs to
touch one of these files must show that the excluded claim is untouched.

## Place and settlement contracts (excluded data ownership)

Place keys, place order, coordinates, exteriors, doorway names, topology and settlement descriptions/culture stay exactly as authored. A personnel edit may change who staffs a place or declare it hostless; it may not change what the place is, grant a prohibited institution, or move a location.

| Capability | Unaffected requirements | Affected (id kept, assertion reviewed) |
| --- | ---: | ---: |
| `settlement-place-registry` | 5 | 0 |
| `place-driven-service-sync` | 5 | 0 |
| `npc-persona-card` | 10 | 0 |
| `npc-canonical-age` | 1 | 0 |
| `sample-city-altoria` | 5 | 2 |
| `altoria-hospitality` | 1 | 2 |
| `altoria-learning-and-exchange` | 2 | 1 |
| `altoria-crown-and-watch` | 2 | 1 |
| `altoria-sanctum` | 3 | 1 |
| `ciaran-village-commons` | 1 | 1 |
| `ciaran-village-crafts` | 1 | 1 |
| `ciaran-village-commerce` | 3 | 1 |
| `place-attendant-hosts` | 2 | 1 |
| `human-guild-hosts` | 0 | 3 |

## Clergy, guild and title-tab contracts (excluded)

The clergy ladder and names, the guild-rank titles including 「F級冒險者」, the six codex category tabs and every non-starter title predicate catalog stay unchanged. Category-tab mirrors (Python enum, presentation mirror, `protocol/constants.js`, the JS protocol test) move together only if a tab ever changes, which this change does not do.

| Capability | Unaffected requirements | Affected (id kept, assertion reviewed) |
| --- | ---: | ---: |
| `title-system` | 15 | 3 |
| `guild-exam-restrictions` | 3 | 0 |
| `guild-rank-exams` | 9 | 0 |

## Skill, sexual-act and balance contracts (excluded)

Skill catalogs, sexual-act catalogs, divine mystery/elemental mastery names and every numeric balance value (prices, bands, coefficients, tiers) keep their current owner. This change moves content identity into registry data; it does not retune or rename it.

## Military exception and examiner contracts (deliberately retained, named)

Both `military-equipment` requirements stay unchanged, including the six E-S pairs and their narrow tagged tests; `guild-exam-restrictions` and `guild-rank-exams` statements stay unchanged because examiner kits and normal rank-matched examiner gear depend on them.

| Capability | Unaffected requirements | Affected (id kept, assertion reviewed) |
| --- | ---: | ---: |
| `military-equipment` | 2 | 0 |
| `guild-exam-restrictions` | 3 | 0 |
| `guild-rank-exams` | 9 | 0 |

`Unaffected` means the requirement id is neither removed nor modified by this change: it keeps its
id, its annotation and its assertion. An `affected` column entry is a MODIFIED requirement whose id
is kept but whose assertions are reviewed (see `cutover-matrix.md`); no entry in this table is a
REMOVED id.

`human-guild-hosts` has no unaffected requirement: all three of its current requirements are
MODIFIED. They change *personnel membership* only -- the persistent-person selection, normal
lineage/gear configuration and connected-residence travel -- and explicitly do not change
examiner-facing rank, military gear or examiner statements.

## The named six E-S military pairs

| Pair | Sword key | Armor key | Consumers that stay named |
| --- | --- | --- | --- |
| E | `military_e_sword` | `military_e_armor` | `world/lore/items/vocab.py`, `world/lore/settlements/assortments.py`, `world/lore/guild_adventurers.py`, `world/rules/rulebook/equipment_effects.yaml`, `world/rules/rulebook/guild_exam_restrictions.yaml`, `world/rules/rulebook/commerce/altoria.yaml` |
| D | `military_d_sword` | `military_d_armor` | `world/lore/items/vocab.py`, `world/lore/settlements/assortments.py`, `world/lore/guild_adventurers.py`, `world/rules/rulebook/equipment_effects.yaml`, `world/rules/rulebook/guild_exam_restrictions.yaml`, `world/rules/rulebook/commerce/altoria.yaml` |
| C | `military_c_sword` | `military_c_armor` | `world/lore/items/vocab.py`, `world/lore/settlements/assortments.py`, `world/lore/guild_adventurers.py`, `world/rules/rulebook/equipment_effects.yaml`, `world/rules/rulebook/guild_exam_restrictions.yaml`, `world/rules/rulebook/commerce/altoria.yaml` |
| B | `military_b_sword` | `military_b_armor` | `world/lore/items/vocab.py`, `world/lore/settlements/assortments.py`, `world/lore/guild_adventurers.py`, `world/rules/rulebook/equipment_effects.yaml`, `world/rules/rulebook/guild_exam_restrictions.yaml`, `world/rules/rulebook/commerce/altoria.yaml` |
| A | `military_a_sword` | `military_a_armor` | `world/lore/items/vocab.py`, `world/lore/settlements/assortments.py`, `world/lore/guild_adventurers.py`, `world/rules/rulebook/equipment_effects.yaml`, `world/rules/rulebook/guild_exam_restrictions.yaml`, `world/rules/rulebook/commerce/altoria.yaml` |
| S | `military_s_sword` | `military_s_armor` | `world/lore/items/vocab.py`, `world/lore/settlements/assortments.py`, `world/lore/guild_adventurers.py`, `world/rules/rulebook/equipment_effects.yaml`, `world/rules/rulebook/guild_exam_restrictions.yaml`, `world/rules/rulebook/commerce/altoria.yaml` |

Tests that must keep naming them (each keeps its id and its reason):

- `world/lore/tests/test_items.py` -- item registry content contract (123-item roster is replaced by
  per-item metadata validation in WP6, but the military keys stay valid registered items).
- `world/rules/tests/test_equipment_effect_rulebook.py` -- the named military data-contract case
  (`military_s_sword` budget check at the `:994` region) stays a named test with unchanged arithmetic.
- `world/lore/tests/test_assortments.py` -- `MILITARY_ADDED_KEYS` (`:65`) is the one piece of the
  historical capital union that survives: WP6 keeps it as a separate tagged military membership test
  with the examiner dependency in its rationale, and drops the historical whole-capital union around it.

## What the four excluded families keep

| Excluded data ownership | Still owned by | Evidence it is not migrated |
| --- | --- | --- |
| Place keys, order, coordinates, exteriors, doorway names, topology | the place registry and the map data | `world/lore/tests/test_settlements.py`, `world/maps/tests/test_service_interiors.py`, `world/maps/tests/test_altoria_capital.py`, `world/maps/tests/test_village_ciaran.py` keep their assertions; WP4 removes only host-identity and offered-item snapshots |
| Settlement descriptions and culture | the place registry | the `sample-city-altoria` xyzgrid delta keeps every topology, permanent-interior and doorway scenario; only selected merchandise-membership bodies change |
| Clergy ladder, guild-rank titles, six category tabs | `title-system` and its four mirrors | no delta removes or renames those requirements; the four mirrors are not edited by this change |
| Skill catalogs, sexual-act catalogs, divine mystery/elemental mastery names, balance values | their current capabilities and rulebook YAML | this change's deltas touch neither the catalogs nor the numeric rulebook values |
| Examiner-facing rank/military statements | `military-equipment`, `guild-exam-restrictions`, `guild-rank-exams` | all three capabilities are listed as retained dependencies, not modified capabilities |

If a later package finds it must weaken one of these assertions to make its own suite pass, that is a
scope change: stop and surface it instead of absorbing it.
