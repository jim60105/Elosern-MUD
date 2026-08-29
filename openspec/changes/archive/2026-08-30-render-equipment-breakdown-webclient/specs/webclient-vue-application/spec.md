## ADDED Requirements

### Requirement: The character UI renders server breakdown without recomputation

The Vue application SHALL render character stat rows from the version-5
payload's `layers` in payload order with verbatim registry names and
kind-formatted signed amounts, SHALL render ALL layers without
truncation, SHALL NOT sort, recompute, regroup, or re-total layer data,
and layer-free rows SHALL keep their existing value text with no
breakdown elements rendered. Equipment rows in the doll and inventory
surfaces SHALL print the server-generated adjustment string verbatim (the
inventory sources it by joining the server's character equipment rows on
`item_key`; a bag-only item renders none; empty renders nothing), and the
intimate view SHALL show the payload's effective exposure value. Only
schema version 5 SHALL be accepted at every wire validator; an unknown
layer `source`/`kind` SHALL still be rejected on the wire, and neutral-
chip fallback exists only as direct-render defense in the component.

#### Scenario: Layer chips mirror the payload exactly

- **WHEN** the drawer renders a defense row whose payload layers are a
  skill mult, a condition flat, and an equipment flat in that order
- **THEN** three chips appear in that order with the payload names and
  kind-formatted amounts, and the value line keeps the existing gauge or
  static text

#### Scenario: No layers, no breakdown elements

- **WHEN** a stat row carries an empty layers list
- **THEN** the value line is unchanged from today and no chip container or
  wrapper element renders

#### Scenario: Adjustment text is verbatim and joined

- **WHEN** an equipped item's character row carries 「攻擊 −2｜防禦 +8｜
  敏捷 −10%｜生命上限 +15」 and the same item appears in the inventory
  equipment list
- **THEN** doll and inventory both print exactly that string, and a
  bag-only item prints nothing

#### Scenario: Effective exposure is proven, not vacuous

- **WHEN** the fixture carries a worn bias-bearing item whose stored-base
  exposure differs from the effective ordinal
- **THEN** the intimate view renders the effective ordinal and the stored-
  base ordinal is asserted absent

#### Scenario: Version 4 payloads are rejected at every wire

- **WHEN** a character payload at schema version 4 reaches the Vue store
  path or the legacy client, or a v5 payload carries a layer with a source
  outside the closed set
- **THEN** every wire validator rejects it; only a direct component render
  with hand-built props exercises the neutral 其他 chip fallback while the
  value line stays correct
