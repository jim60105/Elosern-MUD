## MODIFIED Requirements

### Requirement: The character head card renders only backed identity
The character head card SHALL render exactly the identity the committed payloads carry: a glyph
portrait tile derived from the display name in `status.actor.name`, a numeric badge from the
`magic_power` trait row's current value, that display name, a guild line pairing the guild rank
and merit from `character.guild` (rendering an explicit 未加入公會 marker when the actor has no
guild), the wallet from `character.wallet` formatted as thousands-grouped integer copper, and an
explicit disguise marker when `status.disguise_active` is true. The deleted magic-rank title
ladder SHALL NOT be reconstructed client-side: the card shows no magic-derived rank word in any
form, because the growth redesign retired that display system (the title-system change line owns
title display).

The portrait tile SHALL be a glyph and SHALL NOT contain an image element: the player is never a
present focusable subject of their own exploration catalog, so no portrait asset exists for them
and none SHALL be invented. An empty or absent display name SHALL render an empty tile rather than
a substitute character.

The card SHALL NOT render a race, subrace, class, or faction line in any form — not as a value, not as
a placeholder, and not as an unknown marker — because no such field exists in the `status` or
`character` payload. When a disguise is active, the badge and the guild line SHALL render the
**true** trait value; a displayed disguise value SHALL NOT be substituted for it.

The head card SHALL be the client's single persistent wallet surface.

#### Scenario: The head card renders the backed identity fields
- **WHEN** the `status` and `character` panels are committed for an actor with a magic power, a guild rank and merit, and a wallet balance
- **THEN** the card shows the glyph portrait tile with the numeric magic-power badge, the display name, the guild rank paired with the merit, and the thousands-grouped wallet in copper, and no magic-rank word appears anywhere on the card

#### Scenario: No race, class, or faction line is rendered
- **WHEN** the head card renders for any actor
- **THEN** no race, subrace, class, or faction value, placeholder, or unknown marker appears anywhere on the card

#### Scenario: The portrait is a glyph, never an image
- **WHEN** the head card renders outside combat
- **THEN** the portrait tile contains a glyph derived from the display name and contains no image element and no asset URL

#### Scenario: An active disguise leaves the true magic power on the card
- **WHEN** a disguise is active and the `character` payload's displayed rows carry a magic-power value that differs from the true trait
- **THEN** the badge renders the true trait value, and the displayed disguise value does not replace it

#### Scenario: A guild-less actor shows the explicit marker
- **WHEN** the head card renders for an actor whose `character.guild` carries no rank
- **THEN** the guild line shows the 未加入公會 marker rather than an invented rank

#### Scenario: The wallet has one persistent surface
- **WHEN** the HUD renders with the `character` panel available
- **THEN** the wallet is present on the head card and no other persistently-visible HUD surface renders a second wallet figure
