## Purpose

Let one item cost different amounts in different places while remaining one
item, by resolving a place's final offer from a shared base, a local scale
and explicit per-item exceptions.

## ADDED Requirements

### Requirement: A place's final offer is a shared base adjusted by one local rule
A place's offer for an item SHALL be resolved as either the per-item
override the place declares for that item, or the item's assortment base
adjusted by the place's price scale. An override SHALL take precedence and
SHALL NOT be scaled.

The price scale SHALL be an integer percentage where 100 is par. A place
SHALL inherit its settlement's scale unless it declares its own. Scaling
SHALL be integer arithmetic with deterministic half-up rounding; no
floating-point value SHALL enter the money path at any step.

Exactly one multiplication SHALL be applied to any base value, so the
resolved price does not depend on the order in which adjustments are
combined.

#### Scenario: One item carries two prices and stays one item
- **WHEN** two places offer the same item key, one at the scaled assortment
  base and one at an override
- **THEN** each charges its own price, and an item bought at either place is
  the same item key backed by the same item definition

#### Scenario: A scale is applied once and rounded deterministically
- **WHEN** a place declares a scale other than par
- **THEN** every non-overridden offer is the base multiplied by that scale
  once, rounded half-up to whole copper, with no float produced

#### Scenario: An override ignores the scale
- **WHEN** a place declares both a non-par scale and an override for an item
- **THEN** that item is charged the override exactly, unscaled

#### Scenario: A place inherits its settlement's scale
- **WHEN** a place declares no scale of its own
- **THEN** its offers resolve at its settlement's scale

### Requirement: An override is complete or rejected
A per-item override SHALL declare every field of an offer rule — buy price,
sell price, maximum stock, initial stock and restock quantity — and SHALL
wholly replace the assortment's rule for that item.

A partially declared override SHALL fail catalog load naming the place, the
item and the missing fields. A half-specified rule implies a silent merge
between two sources, which the load-time contract exists to prevent.

An override naming an item the place does not offer SHALL fail catalog load.

#### Scenario: A partial override fails load
- **WHEN** a place declares an override carrying a price but no stock fields
- **THEN** catalog validation raises naming the place, the item and the
  missing fields

#### Scenario: An override for an unoffered item fails load
- **WHEN** a place declares an override for an item that is in none of its
  assortments and is not one of its additions
- **THEN** catalog validation raises naming the place and the item

### Requirement: A place may add and remove individual items
A place SHALL be able to stock an item outside its assortments, and to
decline an item inside them. Its offered goods SHALL be the union of its
assortments' items, plus its additions, minus its removals.

An addition belongs to no assortment and therefore has no base rule, so
every addition SHALL carry a complete override. An addition without one
SHALL fail catalog load naming the place and the item.

A removal naming an item none of the place's assortments contains SHALL fail
catalog load, so a rename that orphans a removal is caught rather than
silently doing nothing.

#### Scenario: A stocked curiosity needs no assortment of its own
- **WHEN** a place declares one addition with a complete override
- **THEN** that item is purchasable at that place at the override price, and
  no other place referencing the same assortments stocks it

#### Scenario: An addition without an override fails load
- **WHEN** a place declares an addition for which it declares no override
- **THEN** catalog validation raises naming the place and the item

#### Scenario: A removal that matches nothing fails load
- **WHEN** a place declares a removal for an item none of its assortments
  contains
- **THEN** catalog validation raises naming the place and the item

### Requirement: Resolved prices are validated, not the bases
Every rejection the catalog applies to a price SHALL be evaluated against
the resolved value a player would be charged, not against the assortment
base. The resolved buy price SHALL lie inside the item's price band, the
resolved sell price SHALL NOT exceed the resolved buy price, and every
resolved money value SHALL be a non-negative integer.

A price scale SHALL be rejected unless it is an integer within a bounded
sane range; a scale of zero or a negative scale SHALL be rejected.

Every such rejection SHALL occur at catalog load, before any registry or
merchant state changes, and SHALL NOT be deferred to the moment a player
attempts the trade.

#### Scenario: Scaling out of the price band fails load
- **WHEN** a scale pushes a resolved buy price above the item's price-band
  ceiling
- **THEN** catalog validation raises naming the place, the item and the
  resolved value, even though the unscaled base was legal

#### Scenario: Scaling that inverts buy and sell fails load
- **WHEN** rounding at a given scale would leave a resolved sell price above
  the resolved buy price
- **THEN** catalog validation raises naming the place and the item

#### Scenario: An out-of-range scale fails load
- **WHEN** a scale is zero, negative, non-integer, or beyond the permitted
  maximum
- **THEN** catalog validation raises naming the declaring settlement or
  place
