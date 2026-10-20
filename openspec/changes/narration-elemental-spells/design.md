# Design

This change authors content inside the contract established by
`narration-core-and-combat-prose`; read that design first. Selection, bounds, bands and
pipeline integration are unchanged.

## D1. One row per spell, one module per element

Eight data modules (`data_fire.py`, `data_water.py`, `data_wind.py`, `data_earth.py`,
`data_lightning.py`, `data_ice.py`, `data_light.py`, `data_dark.py`) mirror the registry's own
element slices, so an author reviewing fire spells sees the same order in both places. Each row
carries one or two `action` variants: the spell's own invocation, never its result — the shared
outcome pools already say whether the strike landed and how hard.

Rejected: family-only authoring with an element vocabulary table. It would keep 火焰箭 and
火球術 identical, which is exactly what this change is for.

## D2. Element register

| element | imagery | avoid |
| --- | --- | --- |
| 火 | heat, ember, ignition, scorched air | 內力/真氣 register |
| 水 | tide, flow, weight of water, quiet pressure | modern plumbing imagery |
| 風 | pressure, cut air, drift, sudden stillness | weather report language |
| 土 | ground, weight, stone rising, footing | geology terms |
| 雷 | instant, white line, thunder after the fact | electrical/technical terms |
| 冰 | still air, fracture, frost creeping, held breath | thermodynamic terms |
| 光 | radiance, warmth, clarity, gentle severance | liturgical rite wording (that is the rite family) |
| 暗 | absence, erosion, whisper, things not seen | gore, cruelty-as-spectacle |

Shape matters as much as element: a single-target spell addresses one body; an area spell
addresses the field (and may name no participant, keeping its slot count at zero or one).

## D3. Verification

- Coverage: exact key-set equality between each element's ACTIVE spells and its authored rows.
- Distinctness: within one element, two spells' openings selected under the same inputs differ;
  across elements, the element vocabulary never collides (a test samples the first line of each
  row and asserts the element registers do not share a line).
- All rows inherit the catalog validator's bounds, slot and no-digit checks.

## Traceability

The delta's requirements are covered by the coverage-contract slice in
`world/skills/tests/test_skill_registry/test_narration_coverage.py` (per-element key-set
equality and the cross-element distinctness check, tagged `Data-contract test:`) and the area
rendering assertion in `world/rules/tests/test_event_narration_pipeline.py`. Both modules
already exist and already carry a shard owner, so no manifest entry and no new test module is
added.

## Risks / Trade-offs

- **115 hand-authored lines in one day.** Each line is short (a clause, not a paragraph) and the
  element vocabulary is fixed by D2, so the work is bounded; the per-element split lets an
  interrupted session leave a valid catalog with the remaining elements still pending — but the
  pending set is one constant for the whole family, so partial landing must keep elemental magic
  pending until all eight modules are in.
- **Tone repetition inside an element** (13 fire spells). The shape and the spell's own effect
  (single, area, buff, scorch, drain) are the differentiators; the distinctness test catches
  outright duplicates, not sameness of mood.
