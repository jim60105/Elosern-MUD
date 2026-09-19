## ADDED Requirements

### Requirement: The damage effect's school segment is validated at parse
`parse_effect`'s `damage` branch SHALL reject a school segment outside the closed set `{"physical",
"magic"}` with `ValueError`, at parse time and therefore at registry load, exactly as it already
rejects an empty element or an empty/malformed school segment. The element segment SHALL remain
unvalidated against `world.lore.elements.ELEMENT_REGISTRY` at this layer — that check stays a
cast-time-only concern (see the following requirement) because a broad set of test fixtures
deliberately author non-registry element tokens that must keep constructing.

#### Scenario: A malformed school fails at registry load
- **WHEN** `parse_effect("damage:fire:sonic")` is called
- **THEN** it raises `ValueError`, and if this string appears in `SKILL_REGISTRY`, the module fails
  to import — a server startup failure, not a runtime no-op

#### Scenario: Every existing valid school keeps parsing unchanged
- **WHEN** `parse_effect("damage:<element>:physical")` or `parse_effect("damage:<element>:magic")` is
  called for any element string previously accepted
- **THEN** it returns the same `DamageEffect` it returned before this change

### Requirement: The damage:<element>:<school> grammar has exactly one parser
`world.skills.effects.parse_effect` SHALL be the only function in the codebase that splits or
validates the `damage:<element>:<school>` string shape. Any other module that needs the parsed
element or school SHALL obtain it by calling `parse_effect` (directly, or through a thin wrapper that
calls `parse_effect` and layers only validation `parse_effect` deliberately excludes) rather than
independently re-implementing the string split. A cast-time-only concern excluded from
`parse_effect` by design — validating a non-`None` element against
`world.lore.elements.ELEMENT_REGISTRY` — MAY be layered on top of `parse_effect`'s result by such a
wrapper, but MUST NOT re-derive the element or school from the raw string a second time.
`DamageEffect.element` is `str | None` (the reserved `damage:none:<school>` token parses to
`element=None`, denoting the absence of an element); the wrapper's cast-time element check MUST treat
`None` as always legal — never evaluating "not a registry key" for the elementless sentinel — the same
way `parse_effect`'s own damage branch already does.

#### Scenario: The cast-time wrapper delegates instead of re-parsing
- **WHEN** `world/rules/combat.py`'s cast-time damage-effect helper is inspected
- **THEN** it calls `parse_effect` to obtain the element and school and contains no independent
  `effect_id.split(":")` or `effect_id.partition(":")` logic of its own

#### Scenario: A cast-time-only rejection still fires through the wrapper
- **WHEN** a `damage:<element>:<school>` effect names a non-`None` element that is not a key in
  `world.lore.elements.ELEMENT_REGISTRY`, and this effect is resolved through
  `ActionResolver.resolve()` in real combat
- **THEN** the action is rejected with `RejectReason.EFFECT_RESOLUTION_FAILED`, identically to the
  behavior before this change

#### Scenario: An elementless damage effect is never rejected by the cast-time element check
- **WHEN** a `damage:none:<school>` effect is resolved through `ActionResolver.resolve()` in real
  combat
- **THEN** the action is not rejected by the cast-time element-registry check — the parsed element is
  `None`, not a registry key, and `None` is always legal
