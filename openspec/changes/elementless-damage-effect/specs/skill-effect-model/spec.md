## ADDED Requirements

### Requirement: A damage effect can declare the absence of an element
`parse_effect` SHALL accept the reserved element segment `none` on the `damage` prefix, returning a
typed damage effect whose element is `None` and whose school is the declared school. Every other
element segment SHALL keep parsing exactly as before, and the parsed element SHALL remain a value no
settlement path consumes: the school selects the attacking stat, and elemental affinity scales
practice only for a skill whose own element appears on a magic-school damage effect, which an
elementless effect can never satisfy.

#### Scenario: The reserved token parses to an absent element
- **WHEN** `parse_effect("damage:none:physical")` is called
- **THEN** it returns the damage effect type with an absent element and the school `physical`, and the
  same call for every registry element key returns that element unchanged

### Requirement: An elementless damage effect and a declared skill element are mutually exclusive
A skill definition SHALL fail construction when it declares an element together with an elementless
damage effect: the two authorities would then disagree about whether the skill has an element, and
presentation reads one while the effect declares the other. The check is one-directional by design —
an element-bearing damage effect on a skill that declares no element stays legal, because that shape
predates this change across shipped and synthetic definitions and is not this change's concern. A
skill with no damage effect at all SHALL be unaffected.

#### Scenario: An elementless effect on an element-bearing skill fails at load
- **WHEN** a skill is constructed declaring an element together with an elementless damage effect
- **THEN** construction raises with the contradiction named, and the same failure occurs at module
  import when such a definition is placed in the shipped registry — a startup failure, never a silent
  runtime mismatch

#### Scenario: A consistent or pre-existing declaration still constructs
- **WHEN** a skill declares no element with only elementless damage effects, or declares an element
  with damage effects of that element, or declares no element alongside an element-bearing damage
  effect, or declares no damage effect at all
- **THEN** construction succeeds and the definition exposes its declared element unchanged
