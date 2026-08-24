## MODIFIED Requirements

### Requirement: Required desktop surfaces remain visible and usable
The narrative SHALL occupy the visual centre of the stage as a bounded caption whose complete log is
reachable in one action, with the brand, the top-meta pill, the HUD island stack, and the action dock
visible at 1440x900 and 1280x720. The action dock, the narrative caption, and the command line SHALL
NOT be permanently closable; every other surface MAY be opened on demand and closed. The foundation
SHALL target desktop only and SHALL NOT claim mobile acceptance. The shell SHALL show the game name as
its brand and SHALL show the current location, the world date/time, and the connection state in a
top-meta surface, with the connected state marked by an ok-green dot paired with a label — never a raw
mode label in place of location. The action dock SHALL render as the approved command surface: a
seal-red frame, a guidance line naming the shortcuts (direction keys to choose, Enter to confirm,
Escape to return, `/` to open the command input), and its items as grid buttons, with the focused cell
marked by a seal-red fill plus a leading glyph, unfocused cells bordered, and disabled cells dimmed but
focusable for their explanation. Submenus SHALL render as an item grid beside a detail pane that names
the focused item, its availability, and the next key action.

#### Scenario: Standard desktop viewport contains every required surface
- **WHEN** the shell renders at 1440x900
- **THEN** the narrative caption, the brand, the top-meta surface, the HUD island stack, the action dock, and the command-drawer control are visible without overlapping the narrative input path

#### Scenario: Minimum desktop viewport remains usable
- **WHEN** the shell renders at 1280x720
- **THEN** every required surface remains reachable and the player can read narrative, open the complete log, inspect status, and open the command drawer

#### Scenario: The complete narrative stays reachable from the bounded caption
- **WHEN** the narrative holds more lines than the bounded caption can display
- **THEN** the player reaches the complete retained log in one action from the caption card

#### Scenario: Mounting the shell retires the degraded text fallback
- **WHEN** the Vue SPA shell mounts into its container
- **THEN** the degraded stock text fallback (`#messagewindow`) is hidden so it cannot stack with the mounted shell in normal document flow and push required surfaces below the visible viewport

#### Scenario: The shell identifies brand, location, time, and connection without a mode label
- **WHEN** the shell is connected in exploration mode
- **THEN** the brand shows the game name, the top-meta surface shows the current location label from the synced status panel, the world date/time, and an ok-green "● 已連線" indicator, and no raw mode label is rendered

#### Scenario: The action dock renders as a framed grid with a guidance line
- **WHEN** the action dock is mounted in any mode
- **THEN** it is framed in seal red, carries a guidance line naming the shortcut keys, renders its current menu items as grid cells with a shape-marked focused cell and dimmed disabled cells, and its submenus show a detail pane beside the item grid

### Requirement: The WebClient loads a local Vue SPA desktop shell
The project WebClient SHALL load Evennia's existing transport together with a locally built,
self-contained Vue 3 single-page application. It SHALL make no remote request for a runtime UI
dependency. The application SHALL provide the required brand, narrative, scene, status, local-map,
action-dock, and command-drawer surfaces and SHALL render them as self-identifying surfaces — the
narrative caption, status resources, map legend, scene label, dock menu, and prompt line — never as a
tab-title component strip. The `local-map` surface SHALL render the `webclient-local-map` panel owned
by the `map-knowledge-minimap` delivery unit. The `scene` surface SHALL render the validated
`webclient-art-panel` payload as the stage backdrop: the current scene when the panel is available,
and a truthful degrade to the mode's gradient stage (never an invented image) whenever the asset is
missing, pending without a prior image, failed, invalid, or the OOB channel is unavailable.

#### Scenario: Offline page load has its UI dependencies
- **WHEN** the WebClient is opened with all non-local network requests blocked
- **THEN** the transport code, the Vite-built Vue application, the project modules, and the theme load from the project origin without a CDN failure

#### Scenario: The minimap renders while the scene degrades to its gradient stage
- **WHEN** the shell renders the local_map payload and the art panel is unavailable, missing, or failed
- **THEN** the local-map surface renders the validated `local_map` payload, and the stage backdrop renders the mode gradient with no invented image

#### Scenario: The scene renders when the validated panel is available
- **WHEN** the `webclient-art-panel` payload is available in the current snapshot
- **THEN** the stage backdrop renders the scene cover-cropped behind the HUD surfaces, with the scene label and alternative text rendered as text outside the bitmap

#### Scenario: The shell renders self-identifying surfaces without a tab strip
- **WHEN** the shell mounts
- **THEN** no tab-title chrome is rendered anywhere, every required surface is present, and each surface carries its own self-identifying content instead of a component-name tab title
