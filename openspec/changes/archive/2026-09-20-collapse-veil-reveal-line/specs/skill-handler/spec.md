## ADDED Requirements

### Requirement: The disguise layer has an unconditional reveal primitive
A deterministic-core reveal primitive SHALL exist in the same module as the disguise write, clearing a
target's disguise layer and its placement record whenever the target carries a veil. It SHALL be
reachable from a skill through a bare, payload-free `reveal_disguise` effect prefix whose handler
declares the `traits` surface.

The primitive SHALL take NO strength argument and SHALL NOT branch on any property of the veil it
finds: this world admits exactly one grade of veil, because only the bloodline-gated divine mystery
can write one, so a reveal either lifts what it finds or finds nothing. It SHALL NOT read the
placement record, which belongs to the veil verb's self-cast branch alone.

A reveal against an unveiled target SHALL be a reported no-op rather than a rejection, so the attempt
neither leaks the absence of a veil through a rejection reason nor fails the action. The primitive
SHALL NOT expose true trait values, identity, or persona; its only effect is removing a veil.

#### Scenario: A reveal lifts an authored veil
- **WHEN** a reveal resolves against a target carrying an authored disguise declaration
- **THEN** the target's disguise layer and placement record are cleared and `get_display_value`
  returns true values

#### Scenario: A reveal lifts a veil the verb placed
- **WHEN** a reveal resolves against a target whose veil was written by the veil verb during play
- **THEN** the target's disguise layer and placement record are cleared

#### Scenario: No weaker reveal can be expressed
- **WHEN** a skill declares any payload on the `reveal_disguise` prefix
- **THEN** the registry fails to load, because a reveal that stops at some veils cannot be spelled:
  every reveal that parses pierces any veil

#### Scenario: A reveal against an unveiled target is a clean no-op
- **WHEN** a reveal resolves against a target carrying no disguise layer
- **THEN** the action completes without raising and changes no stored state

#### Scenario: A reveal never exposes anything but the veil's removal
- **WHEN** any reveal resolves
- **THEN** the only state it touches is the target's disguise layer and placement record; no true
  trait value, identity field, or persona record is read or written

## REMOVED Requirements

### Requirement: The disguise layer has a provenance-scoped reveal primitive
**Reason**: The requirement mandates exactly two reveal strengths — one that clears a mundane veil
and stops at a divine one, and one that clears either — and a pierce test that branches on the veil's
provenance to choose between them. Nothing in this world veils an entity except the bloodline-gated
divine mystery, so the weaker strength has no target it can legitimately stop at and no target it can
legitimately clear. Keeping it expressible meant a skill could be authored against it and strip the
veils the setting guarantees are unstrippable, which is the defect this change fixes. The replacement
requirement states an unconditional reveal with no strength vocabulary at all.

**Migration**: `reveal_can_pierce(entity, strength)` becomes `reveal_can_pierce(entity)` and reports
only whether a veil is present; `reveal_disguise_effect(entity, strength)` loses its second
parameter and keeps its cleared / reported-no-op return contract. The `reveal_disguise:true_name`
effect form stops parsing — `true_name_sight` declares the bare `reveal_disguise` prefix instead —
and no skill may declare a payload on that prefix afterwards.
