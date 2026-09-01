## ADDED Requirements

### Requirement: The wilderness payload legend states the cell scale from the provider constant
The `local_map` presenter SHALL, for the `wilderness` layer only, append one localized scale note
to the payload `legend` after the four visibility-state labels, whose text states the wilderness
cell size in kilometres derived at build time from
`world.maps.wilderness_provider.WILDERNESS_KM_PER_CELL` — no module or client code SHALL
duplicate the constant or the conversion. The four state labels SHALL keep their existing order
and positions, so the scale note is the fifth entry. Payloads for the `grid`, `instance`, and
`interior` layers SHALL keep their legend exactly as before (the four state labels). The extended
legend SHALL remain within the existing bounds (at most 16 entries, 256 code points each) and
SHALL pass both validators unchanged — no payload schema field is added or altered.
The presenter SHALL read the constant as an attribute of its owning module at legend-assembly
time (never a value imported into the presenter's own namespace), so patching the provider
module attribute is observed by the presenter.

#### Scenario: A wilderness payload legend carries the scale note
- **WHEN** the `local_map` presenter builds an available payload for a `TerrainRoom`
- **THEN** the legend is the four state labels followed by one entry whose text contains the
  string form of `WILDERNESS_KM_PER_CELL` (e.g. `每格約 10 公里`), and the payload passes the
  exact Python validator

#### Scenario: Non-wilderness layers are untouched
- **WHEN** the presenter builds available payloads for grid, instance, and interior rooms
- **THEN** each legend equals the four state labels exactly, with no scale note

#### Scenario: The scale note follows the single constant
- **WHEN** a test patches `world.maps.wilderness_provider.WILDERNESS_KM_PER_CELL` to a
  different integer and rebuilds a wilderness payload
- **THEN** the scale note's kilometre figure equals the patched value, proving the note is
  derived from the provider constant rather than a duplicated literal

### Requirement: The legend renders beyond-state entries as neutral info chips
The shared map renderer SHALL render each legend entry beyond the four visibility-state labels
with a dedicated neutral info-chip treatment — design-token colors only, text as the primary
carrier — and SHALL NOT style it by cycling the four state chip styles. The first four entries
SHALL keep their state chip treatments and order exactly as before, the overlay SHALL remain the
only legend surface (the minimap island renders no legend element for any payload), and the
info entry's distinction from state entries SHALL NOT rely on colour alone.

#### Scenario: The overlay shows four state chips and one info chip
- **WHEN** the full-map overlay renders a wilderness payload whose legend carries the scale note
- **THEN** the legend lists five entries, the first four keep their state chip treatments in the
  fixed order, and the fifth renders with the neutral info-chip treatment distinct from all four
  state treatments

#### Scenario: Extra entries never masquerade as visibility states
- **WHEN** a payload legend carries any entry beyond the fourth (present-day or future)
- **THEN** that entry renders with the info-chip treatment, not with any of the four state chip
  classes, and its text label is rendered in full

#### Scenario: The island still renders no legend
- **WHEN** a wilderness payload with the scale note renders on the minimap island
- **THEN** no legend element exists anywhere in the island's DOM, exactly as for every other
  payload
