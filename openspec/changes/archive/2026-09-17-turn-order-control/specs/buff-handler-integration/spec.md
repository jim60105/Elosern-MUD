## ADDED Requirements

### Requirement: Buff definitions may declare a validated in-round order operation
A buff definition MAY declare a closed-vocabulary in-round order-operation clause at definition
load — one operation value drawn from exactly {advance_to_head, retreat_to_tail} in a well-formed
wrapper mapping —
carried on the loaded definition beside the shipped marker clause. A malformed declaration (an
unknown operation word, a bare string instead of the wrapper, a boolean, a number, or extra keys)
SHALL raise at load time naming the offending definition key, fail-closed like every other
definition-shape clause. The clause is definitional data only: a row declaring it with no
round-loop consumer present SHALL load and apply exactly like an ordinary timed row, and the
definition SHALL remain applyable, refreshable, and removable through the ordinary `BuffHandler`
lifecycle with no ordering side effect of its own.

#### Scenario: A well-formed order row loads and cycles through the ordinary lifecycle
- **WHEN** a synthetic row declaring the advance-to-head operation value is loaded, applied to a living
  entity, refreshed, and expired with no combat round running
- **THEN** the loaded definition carries the validated operation and the instance mounts, refreshes,
  and expires through the ordinary `BuffHandler` path with no effect beyond an ordinary timed buff

#### Scenario: Every malformed order clause fails the load closed
- **WHEN** rows declare an unknown operation word, a bare operation string without the wrapper, a
  boolean, a number, or the wrapper with extra keys
- **THEN** each raises at load time naming the offending definition key and no definition is
  produced, while every previously valid row file loads unchanged
