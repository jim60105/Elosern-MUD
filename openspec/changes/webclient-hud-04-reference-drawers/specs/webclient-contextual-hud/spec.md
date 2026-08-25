## ADDED Requirements

### Requirement: Reference surfaces render in a right-anchored drawer with one modal contract
The client's reference surfaces SHALL render inside a drawer anchored to the right edge of the stage,
spanning the full stage height, bounded to a width that never exceeds the viewport, drawn on the solid
panel background with a left border so it reads as a surface laid over the stage rather than a region
of it. The drawer SHALL enter and leave by a horizontal slide expressed through the shared motion
tokens, over a blurred scrim that covers the whole stage. Its header, its scrolling body and its
optional footer SHALL be one column, and the body SHALL be the drawer's only scrolling region.

At most one drawer SHALL be open at any time; opening a second SHALL close the first. While a drawer
is open it SHALL trap keyboard focus, so no surface behind it is reachable by sequential navigation.
It SHALL close on Escape, on activation of its labelled close control, and on activation of the scrim,
and every one of those paths SHALL restore focus to the control that opened it. An open drawer SHALL
register itself as an open surface so the stage recession this capability already requires applies
without a second mechanism.

#### Scenario: A drawer opens over the stage with a scrim
- **WHEN** the player opens a reference drawer
- **THEN** the drawer slides in against the right edge for the full stage height over a blurred scrim, its body is the only scrolling region, and the stage behind it carries the recession mark

#### Scenario: Only one drawer is open at a time
- **WHEN** a drawer is open and the player opens a different one
- **THEN** the first drawer closes as the second opens, and exactly one drawer and one scrim are present

#### Scenario: Focus is trapped and returned
- **WHEN** a drawer is open and the player cycles focus forward past its last control and backward past its first
- **THEN** focus stays inside the drawer in both directions, and on closing by Escape, by the close control, or by the scrim, focus returns to the control that opened it

#### Scenario: Closing the last drawer clears the recession
- **WHEN** the open drawer closes and no overlay remains open
- **THEN** the scrim is removed and the stage's recession mark is cleared

#### Scenario: Reduced motion keeps the state and drops the transition
- **WHEN** `prefers-reduced-motion` is set and a drawer opens
- **THEN** the drawer is open and correctly placed with no slide transition played

### Requirement: The reference surfaces have no permanently visible home and are reached from the dock
The skill book, the bag and equipment, the shop, the quest board, the lore reference and the character
status SHALL each render in exactly one place — its drawer — and SHALL NOT be present in the DOM while
that drawer is closed. The stage SHALL carry no permanently visible column of reference panels.

Each drawer SHALL be opened either by the dock frame that owns its surface, or by a single labelled
control inside a drawer that already presents the same read model, or by a surface this capability
names elsewhere as an opener for it. No reference surface SHALL require more than two actions from the
dock's root frame to reach. Opening a drawer SHALL NOT change any dock root item, any menu frame, any
menu key, or the meaning of Escape.

#### Scenario: No reference surface is mounted while the drawers are closed
- **WHEN** the stage renders in exploration mode with every drawer closed
- **THEN** no skill book, bag, shop, quest board, lore reference or character-status element exists in the DOM or in the tab order, and no reference column is rendered

#### Scenario: Every reference surface is reachable from the dock
- **WHEN** the player starts at the dock's root frame
- **THEN** each of the six reference surfaces is reached in at most two actions, and the narrative caption remains the visual centre of the stage

#### Scenario: An emptied right-hand stack costs nothing
- **WHEN** the stage renders at 1440x900 and 1280x720 with every drawer closed
- **THEN** the right-hand HUD anchor renders no reference panel, contributes no visible box and no tab stop, and no stage anchor's rendered box intersects another's

### Requirement: A drawer hosting a dock frame renders that frame rather than a second navigation model
When the keyboard router's current frame belongs to a surface that a drawer presents, that drawer
SHALL be open and SHALL render that frame's rows through the same shared row renderer the dock uses,
beside the surface's own presentation. The client SHALL NOT maintain a second frame stack, a second
focus model, or a second set of menu keys for a drawer.

Closing the drawer SHALL pop exactly one menu level, and leaving that surface by any path SHALL close
the drawer, so no state exists in which such a frame is current while its drawer is closed. A drawer
that presents no router frame SHALL open and close without touching the frame stack at all.

A drawer SHALL be openable only while its backing payload is present. When the committed mode changes
so that a drawer's payload is no longer available, when the presentation epoch resets, or when the
transport is lost, every open drawer SHALL close and every local selection, quantity and confirmation
state inside it SHALL be discarded.

#### Scenario: A hosted frame renders inside its drawer
- **WHEN** the player opens a service surface whose frame the router pushes
- **THEN** the matching drawer opens, that frame's rows render inside it through the shared row renderer with the focused row marked and disabled rows focusable, and the dock renders no duplicate copy of those rows

#### Scenario: Escape from a hosted frame pops exactly one level
- **WHEN** a drawer is hosting a router frame and the player presses Escape
- **THEN** exactly one menu level closes, the drawer closes with it, focus returns to the opener, and no action is dispatched

#### Scenario: A drawer with no frame leaves the router alone
- **WHEN** the player opens the character-status drawer, which pushes no menu frame
- **THEN** the router's frame stack is unchanged, and closing the drawer pops nothing

#### Scenario: A mode change closes the drawers it invalidates
- **WHEN** the committed mode changes from exploration to combat while a services-backed drawer is open
- **THEN** that drawer closes, its local selection, quantity and confirmation state is discarded, and no stale service surface remains reachable

### Requirement: The bag renders the bounded inventory rows without inventing a total or a rarity
The bag SHALL render the committed `services` panel's inventory rows — each row's display name, its
held count and whether it is equipped — and nothing else. The listing SHALL be bounded by the server's
row ceiling; when it holds that many rows the drawer SHALL state the ceiling in words. The shipped row
count SHALL NOT be presented as a count of the player's untruncated holdings, because the panel's
inventory total is that same shipped count and carries no information about what was truncated.

The bag SHALL NOT render an item rarity, a per-item statistics line, or a comparison tooltip: the
inventory rows carry no such field. It SHALL NOT render a use, consume or equip control, because the
panel advertises no such action. When the `services` panel commits its unavailable form, or when its
inventory section is absent, the bag SHALL render only the registry-owned reason and SHALL fabricate
no wallet, no row and no count.

#### Scenario: The bag lists what the payload carries
- **WHEN** the committed `services` panel carries inventory rows
- **THEN** each row renders its display name, its held count and an equipped marker where the row is equipped, and no rarity, statistic or tooltip is rendered for it

#### Scenario: The ceiling is stated, the total is not invented
- **WHEN** the inventory listing holds the server's maximum number of rows
- **THEN** the drawer states that the listing is bounded at that maximum, and it never renders a figure claiming to be the player's complete holdings

#### Scenario: No use or equip control appears
- **WHEN** the bag renders a held item, whether equipped or not
- **THEN** it offers no use, consume or equip control, matching the panel's action set

#### Scenario: An unavailable services panel fabricates nothing
- **WHEN** the `services` panel commits its unavailable form
- **THEN** the bag renders only the registry-owned reason message, with no rows, no wallet and no count

### Requirement: The equipment doll renders only server-authored slots and drops nothing
The equipment presentation SHALL be built from the committed `character` panel's equipment rows, each
of which carries a slot, an item key and a display name and nothing more. The doll SHALL present the
server's singleton slots as named positions that render an explicit empty state when no row occupies
them, SHALL group the repeatable accessory rows together, and SHALL render any slot key outside the
recognised set as a labelled row rather than discarding it, so no row the payload sends is lost.

The doll SHALL NOT render a statistics line, an attack or defence value, a rarity, or a comparison
against another item: the equipment rows carry none of those. Equipment SHALL be presented as true
values that a disguise does not affect.

#### Scenario: An empty slot is shown as empty
- **WHEN** the committed equipment rows carry no row for a singleton slot
- **THEN** that slot renders its name with an explicit empty state, and no item is invented for it

#### Scenario: Repeated accessories all render
- **WHEN** the committed equipment rows carry more than one accessory row
- **THEN** every accessory row renders in the accessory group, and none is dropped for want of a fixed position

#### Scenario: An unrecognised slot is rendered, not discarded
- **WHEN** an equipment row carries a slot key outside the recognised set
- **THEN** the row renders with its slot key as its label and its display name, and the doll drops no row

#### Scenario: No statistics are invented for an equipped item
- **WHEN** an equipped item renders in the doll
- **THEN** it shows its display name and its slot only, with no attack, defence, rarity or comparison value

### Requirement: The character-status drawer degrades section by section and never substitutes a disguise
The character-status drawer SHALL present the committed `status` panel's resources and its complete
condition roster in every mode, because that panel is available in every mode; each condition SHALL
pair a non-colour severity glyph with its label and every numeric or derived-modifier value the
payload provides. It SHALL present the committed `character` panel's true traits, equipment, guild
standing, wallet and persona background, and SHALL mark each of those sections with the registry-owned
reason when the `character` panel is unavailable — as it is outside exploration mode — rather than
hiding the drawer or inventing a value.

Where a disguise is active the drawer SHALL render the displayed values beside the true trait rows
they describe, distinctly labelled, together with the statement that a disguise affects display,
registration and identification only and that combat always resolves against true values. A displayed
value SHALL NEVER replace a true trait row.

The intimate and adult state block the design draft shows in this drawer SHALL be absent: no arousal,
wetness, shame, exposure, climax-phase, per-part sensitivity or virginity element, and no placeholder
standing in for one, because no committed panel carries such a field.

#### Scenario: The drawer is useful in combat
- **WHEN** the committed mode is combat, so the `character` panel is unavailable
- **THEN** the drawer opens and renders the `status` resources and the complete condition roster, and marks the trait, equipment, guild, wallet and persona sections with the registry-owned reason

#### Scenario: Conditions are never colour-only
- **WHEN** the condition roster renders a committed condition
- **THEN** it pairs a non-colour severity glyph with the condition's label and every numeric or derived-modifier value the payload provides

#### Scenario: A disguise is a comparison, not a substitution
- **WHEN** the committed `character` panel carries an active disguise with displayed values
- **THEN** the drawer renders each displayed value beside the true trait row it describes with an explicit label, states that combat resolves against true values, and shows no true row replaced by a displayed one

#### Scenario: The intimate block is absent
- **WHEN** the character-status drawer renders in any mode
- **THEN** no arousal, wetness, shame, exposure, climax-phase, sensitivity or virginity element is present and no placeholder stands in for one

### Requirement: The drawer layer renders the wallet exactly once
Across every drawer, the player's wallet SHALL be rendered in exactly one place — the character-status
drawer's character section — and SHALL be read from the committed panel that owns it. The shop, the
lore reference and the bag SHALL NOT render a balance of their own. A drawer that cannot read the
wallet from an available panel SHALL render no balance at all rather than a zero.

#### Scenario: One wallet across the whole drawer layer
- **WHEN** every drawer is opened in turn with the `services` and `character` panels available
- **THEN** exactly one wallet value is rendered across all of them, in the character-status drawer

#### Scenario: An unavailable panel renders no balance
- **WHEN** the panel that carries the wallet is unavailable
- **THEN** no drawer renders a balance, and none renders a zero in its place

### Requirement: Mutations issued from a drawer keep the dispatch and confirmation contract
Every affordance inside a drawer SHALL emit exactly the server-authored action identifier and payload
its descriptor carries, through the client's single dispatch entry, and SHALL be governed by the same
in-flight, epoch and revision gates as the same action issued from the dock. A disabled affordance
SHALL remain readable for its server-authored reason and SHALL submit nothing. While mutations are
locked — a submission in flight, an unaccepted revision, or a lost transport — every drawer affordance
SHALL be locked with them.

A destructive service action issued from a drawer SHALL sit behind an explicit confirmation step that
names what it does, with a cancel path that submits nothing. A quantity form inside a drawer SHALL
keep the server-advertised minimum and maximum and SHALL NOT permit a value outside them.

#### Scenario: A drawer affordance dispatches the exact server intent
- **WHEN** the player activates an enabled affordance inside a drawer
- **THEN** exactly one action is emitted carrying the descriptor's own action identifier and payload, through the same dispatch entry the dock uses

#### Scenario: Abandoning a quest from a drawer requires confirmation
- **WHEN** the player activates the abandon affordance on an active quest inside the quest drawer
- **THEN** a confirmation step renders naming the quest and what abandoning does, no mutation is sent, and cancelling returns without submitting

#### Scenario: A locked client locks the drawers
- **WHEN** a submission is in flight, its revision is unaccepted, or the transport is lost
- **THEN** every affordance inside every drawer is locked and emits nothing

#### Scenario: A quantity form keeps the server's bounds
- **WHEN** the player raises a quantity inside a drawer past the server-advertised maximum
- **THEN** the value is clamped to that maximum and no request can authorise a larger quantity
