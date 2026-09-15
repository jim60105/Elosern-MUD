## MODIFIED Requirements

### Requirement: gauge regen is a closed-form computation, never a per-second or per-quantum loop
`world/rules/clock.py` SHALL compute HP/MP/SP regen for a settled entity as
`min(max, current + rate * elapsed_seconds)`, applied once per `advance()` call per entity, regardless
of how large `elapsed_seconds` is. This computation SHALL read `elapsed_seconds` from the `advance()`
call's own argument, never from any wall-clock-timestamp-based mechanism the underlying `GaugeTrait`
implementation might provide. Each gauge's effective rate SHALL first be multiplied by the entity's
merged combat-modifier bundle value `{gauge}_regen_scale` (absent means `1.0`, any authored
non-negative finite scale is legal); a zero scale SHALL freeze that gauge without consuming or
clobbering its carried sub-unit regen remainder, and gauges with no scale row SHALL compute
bit-identically to the pre-change form. The scale lookup SHALL be the existing bundle query, and no
element-, buff- or skill-name branch may participate in the regen stage.

#### Scenario: A large elapsed_seconds value is applied in one step
- **WHEN** `advance()` is called with `seconds=28800` (8 hours) for an entity whose `hp` gauge has
  `rate=2` per second and is below max
- **THEN** the entity's `hp` reflects `min(max, current + 2 * 28800)` after exactly one regen
  computation, not 28,800 individual one-second increments

#### Scenario: Regen never exceeds the gauge's max
- **WHEN** `elapsed_seconds * rate` would push a gauge's value past its configured `max`
- **THEN** the gauge's value is clamped to exactly `max`, never higher

#### Scenario: A zero regen scale freezes without disturbing the remainder
- **WHEN** a synthetic entity carrying a regen-scale-zero rule advances across two separate advances
  while its gauge sits below maximum with a nonzero carried remainder
- **THEN** the gauge value and its remainder are byte-identical after each advance, and a following
  advance after the scale ends resumes the unchanged closed-form arithmetic including the remainder

#### Scenario: Scaled regen is still one closed-form step
- **WHEN** a partial regen scale (e.g. `0.5`) is active for a large `elapsed_seconds`
- **THEN** the gauge reflects `min(max, current + rate * scale * elapsed_seconds)` from one computation
