# Delta spec: webclient-party-panel (companion-possession-webclient)

The `party` panel payload schema is UNCHANGED — the possession controls are client-side drawer
affordances fed from the exploration vocabulary. The PartyDrawer surface requirement is NEW
(adds nothing to the payload contract).

## ADDED Requirements

### Requirement: The party drawer offers possession controls per companion
The Vue PartyDrawer SHALL render, on each companion row, the `explore.possess` affordance from
the shared exploration vocabulary (enabled state and disabled reason exactly as emitted), and
SHALL present the single `explore.possess_release` control while the vocabulary carries one; the
controls SHALL dispatch through the same `ui_action` path as every other affordance. The `party`
panel payload itself SHALL NOT gain any possession field: possession state reaches the client
through the vocabulary and the possession banner only, and the schema-version-1 six-key row
contract is unchanged.

#### Scenario: A possessable companion row offers the action
- **WHEN** the drawer renders a co-located bound companion whose possess entry is enabled
- **THEN** the row carries the 附身 control and dispatching it submits `explore.possess` with the
  companion's id

#### Scenario: A gated companion row shows the gate honestly
- **WHEN** the companion's possess entry is disabled with a gate reason
- **THEN** the row renders the control disabled carrying the emitted reason, never hidden

#### Scenario: The panel payload schema is untouched
- **WHEN** the party panel payload is validated while the player possesses a companion
- **THEN** the payload is byte-identical in shape to the schema-version-1 contract and carries no
  possession field
