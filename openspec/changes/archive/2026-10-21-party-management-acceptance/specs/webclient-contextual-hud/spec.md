# Spec Delta

## ADDED Requirements

### Requirement: The help overlay carries the party management rules
The help overlay SHALL carry the rule explanations the party and shop windows omit: companion follow rules, item transfer rules (out of combat only, free, equipped and locked items excluded), combat restrictions in the party window, the 系譜 node legend (filled, half-filled, dashed, 可解鎖), the shop's single-price convention, and the P B C K L J M hotkeys, in Traditional Chinese, as static authored text with no state.

#### Scenario: Transfer rules live in help, not in the bag
- **WHEN** the player opens 說明 and the party window's 背包 tab in turn
- **THEN** the help overlay explains the transfer rules while the bag shows only counts, controls and committed disabled reasons

#### Scenario: Help explains following under possession
- **WHEN** the help overlay's party section renders
- **THEN** its follow rules state that the whole party, the player's own body included, follows a possessed companion through exits

#### Scenario: The lineage legend is in help
- **WHEN** the help overlay's party section renders
- **THEN** it explains the three node diamond states and 可解鎖 with shape and text, never colour alone

## MODIFIED Requirements

### Requirement: The map, settings, and help surfaces are reachable from the live client
The map, settings and help surfaces SHALL each be reachable from the running client by a labelled control, not only from the component showcase.

#### Scenario: Live triggers open each surface
- **WHEN** the client renders the minimap island and the top navigation bar
- **THEN** the minimap island carries a labelled control that opens the map surface, rendered as a sibling of its map canvas rather than as a wrapper around its actionable nodes — the island's non-interactive body MAY additionally open the same surface on pointer click, which never replaces or wraps the labelled control — and the top navigation bar's labelled 設定 control and the 說明 control in its tool group open the settings and help surfaces, in every mode that renders the top navigation bar, whether the command line is expanded or collapsed

#### Scenario: The map surface tracks read-model replacement
- **WHEN** the committed `local_map` read model is replaced
- **THEN** the map surface renders the payload through the same component the minimap island renders and re-renders its available and unavailable branches whenever that read model is replaced, so a superseded payload never leaves a stale map or a stale reason on screen; when a newly committed payload resolves to the other layout variant, the surface follows the resolved value with no control of its own

#### Scenario: The map opens fitted with exactly its view affordances
- **WHEN** the map surface opens
- **THEN** it opens fitted, showing the whole drawing inside its body, and offers exactly the view affordances the full-map fit-view requirement of the local-map capability defines — wheel and `+` / `-` zoom within that requirement's bounds, labelled 放大 and 縮小 buttons, drag-pan, a labelled 置中 button that recentres the current node, and a `?` disclosure button named 圖例 that opens the state legend in a popover — naming those gestures in words in its guide row

#### Scenario: View affordances change nothing committed
- **WHEN** any map view affordance is used
- **THEN** it changes only the view of the drawing: none changes the committed payload, the resolved layout variant, or any geometry the surface declares, and none is persisted

#### Scenario: The map states no figures
- **WHEN** the map surface renders on any layer
- **THEN** it renders no bearing, compass angle, distance, or coordinate figure, and no zoom level, scale ratio, or other figure describing the view

#### Scenario: The canvas framing is pure CSS
- **WHEN** the map surface's body renders
- **THEN** it carries the redesign draft's map-canvas framing (the radial-gradient dark terrain background painted as pure CSS inside a rounded ink border) and fabricates no terrain geometry the payload does not claim

#### Scenario: The help surface is the client's own truth
- **WHEN** the help surface renders
- **THEN** it renders the client's own control reference — the keys this client binds, the dock's navigation model and the close paths — from a single client-owned source, and states how the game's own help output is reached; it names no key binding or control the client does not implement, describes `/` and the ⌨ toggle as expanding the command line and Escape and a successful send as collapsing it, also renders the static party-management rule reference, and renders no category-to-entry game-help browser, fabricated live state or placeholder for an absent guide panel

#### Scenario: Each surface has a live trigger
- **WHEN** the client renders in exploration mode with the `local_map` panel committed and the command line collapsed
- **THEN** the minimap island carries a labelled control that opens the map surface, and the top navigation bar carries a labelled 設定 control and a labelled 說明 control in its tool group that open the settings and help surfaces

#### Scenario: The map surface tracks read-model replacement in the live client
- **WHEN** the map surface is open and an update replaces the committed `local_map` payload with the registry-owned unavailable form, and then with a different available payload
- **THEN** the surface renders only the registry-owned reason, then the replacement map, and at no point shows a map or a reason from the superseded payload

#### Scenario: The map surface advertises no zoom or pan
- **WHEN** the map surface renders on any layer
- **THEN** its only view controls are the labelled 縮小, 放大, and 置中 buttons and the 圖例 disclosure
  button, its guide row names the wheel, `+` / `-`, and drag gestures in words, the legend appears only
  inside the 圖例 popover, and no zoom level, scale ratio, bearing, compass angle, or distance figure
  appears anywhere on the surface

#### Scenario: The map surface frames the draft canvas without invented terrain
- **WHEN** the map surface renders an available payload
- **THEN** the map body shows the radial-gradient ink background inside the rounded ink frame, and no terrain, coastline, or route geometry is drawn that the payload does not carry

#### Scenario: The help surface tells the truth about what it knows
- **WHEN** the help surface renders with no committed panel carrying authored guide content
- **THEN** it renders the client's own control reference, including `/` and the ⌨ toggle expanding the command line and Escape collapsing it, and a statement of how the game's help output is reached, alongside the static party-management rule reference; it renders no category-to-entry game-help browser, fabricated live state or placeholder for an absent guide panel
