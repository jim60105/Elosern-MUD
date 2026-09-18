## REMOVED Requirements

### Requirement: Unmechanized Divine Mysteries are explicitly declared, not silently missing
**Reason**: The four declared entries (時間加速, 空間扭曲, 物質轉換, 生命延續) are retired by this change.
The redesigned family replaces them with three mechanically live chains, and the four subjects are
documented as deliberately uncatalogued lore with no keys at all — so a requirement asserting that they
exist as declared registry entries no longer describes anything true.
**Migration**: None. No preset, import record, lore registry or rulebook row names the retired keys, and
the project has no released users.

## ADDED Requirements

### Requirement: The divine-mystery family takes no element verb and costs nothing
Every skill in `SkillCategory.DIVINE_MYSTERY` SHALL declare an empty resource cost, SHALL declare
`requires_divine_arts=True`, and SHALL NOT declare any damage or healing effect. The family's effects
SHALL come only from the conferral, revocation, veil and reveal vocabulary — the layer that rewrites who
holds a power, who can see a fact, and how fast someone learns — so the family never supplies, and never
competes with, a combat verb an element tree owns. This is a family-wide invariant that any future node
added to the category SHALL also satisfy.

#### Scenario: No divine-mystery skill carries a cost
- **WHEN** every registered skill in the `DIVINE_MYSTERY` category is inspected
- **THEN** each declares an empty `cost` mapping

#### Scenario: No divine-mystery skill deals damage or heals
- **WHEN** every registered skill in the `DIVINE_MYSTERY` category is inspected
- **THEN** none declares a damage or healing effect

#### Scenario: Every divine-mystery skill is bloodline-gated
- **WHEN** every registered skill in the `DIVINE_MYSTERY` category is inspected
- **THEN** each declares `requires_divine_arts=True`, so a race without divine affinity is refused at
  cast time by the shipped gate

#### Scenario: A race without divine affinity cannot cast any of them
- **WHEN** an entity of a race whose profile reports no divine affinity somehow owns a
  `DIVINE_MYSTERY` skill and casts it
- **THEN** the cast is rejected by the bloodline gate before any resource, roll or effect resolution

### Requirement: Divine-mystery progression composes conferral, veil and reveal behavior
A divine-mystery chain SHALL compose into executable behavior, not into declared-but-inert entries: a
later rung of a conferral chain SHALL produce a strictly larger conferred effect on its target than an
earlier rung of the same chain; a conferral node declaring an ally audience SHALL reach every ally in
the resolved audience rather than only the selected target; and a node declaring several parents SHALL
stay unusable until EVERY declared parent meets its threshold, becoming usable when the last one does.
These contracts SHALL be established over synthetic compositions rather than by restating the shipped
catalog's rows.

#### Scenario: A later rung confers more than an earlier rung
- **WHEN** the same caster confers through an earlier-rung node and then through a later-rung node of
  the same chain onto the same target
- **THEN** the target's resulting effective value is strictly larger after the later rung

#### Scenario: An ally-audience conferral reaches the whole party
- **WHEN** a conferral node declaring an ally audience resolves with several allies in the resolved
  audience
- **THEN** every ally in that audience holds the grant, not only the selected target

#### Scenario: A multi-parent capstone waits for its last parent
- **WHEN** a node declaring three parents has two of them at their thresholds and the third below
- **THEN** the node is not usable, and it becomes usable as soon as the third parent reaches its
  threshold

#### Scenario: A chain root is usable with no prerequisite
- **WHEN** an entity owns a chain-root divine-mystery node and none of its descendants
- **THEN** the root is usable, because a root declares no prerequisite edge
