## ADDED Requirements

### Requirement: The outcome-reaction vocabulary grows one declarative order-marker action
The reaction `then` vocabulary SHALL grow exactly one order-operation action, `mark_order_op`,
naming a buff definition that itself declares an in-round order operation — validated fail closed
at rule load (an unknown definition, or a definition without the order clause, names the offending
rule id; every existing `apply_buff`/`remove_buff`/`pleasure_gain`/`counter_damage`/
`apply_buff_to_source` shape is preserved verbatim). At dispatch the action applies the named
definition as a live instance onto the outcome event's source with the same grant-time attribution,
in-transaction settlement, rollback coverage, sourceless-write no-op, and once-per-event semantics
as the shipped source-targeted actions, and SHALL itself perform no initiative-sequence mutation —
the round loop's declarative fold is the sole consumer of the mounted marker. The action SHALL NOT
combine with the two shipped source-targeted actions in one `then`.

#### Scenario: A ward-shaped rule marks the strike's source
- **WHEN** a synthetic reactor holding the gating buff is struck physically by a living attacker
  while a `physical_hit` rule declaring `mark_order_op` on a retreat-declaring definition is loaded
- **THEN** the attacker holds the live marker instance attributed to the reactor at grant time, the
  initiating strike's damage and practice settlement are unchanged, and no initiative sequence is
  mutated by the dispatch itself

#### Scenario: Sourceless and gated writes apply nothing
- **WHEN** a sourceless write and a strike by an attacker whose mount the rule no longer matches
  settle against the same reactor
- **THEN** no marker instance is applied in either case and every other shipped reaction behavior
  on the reactor is unchanged

#### Scenario: A malformed order-marker rule fails the rule load closed
- **WHEN** rules declare `mark_order_op` naming an unknown definition, a definition without the
  order clause, a bare non-key value, or `mark_order_op` alongside `counter_damage` or
  `apply_buff_to_source`
- **THEN** each raises at load time naming the offending rule id, and every previously valid rule
  file loads unchanged
