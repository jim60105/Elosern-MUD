# Delta spec: webclient-frame-resolution (webclient-align-08-dialogue-surface)

## MODIFIED Requirements

### Requirement: Teardown resets the stack to the mode root from one decision point

Mode switch (exploration / combat / dialogue / creation), presentation epoch reset, transport loss, and no-puppet detach SHALL each replace the whole descriptor stack with exactly one declarative root frame of the new mode — the `exploration.root`, `combat.root`, `dialogue.root`, or `creation.root` descriptor — from the single existing teardown decision point. The stack SHALL never be empty in a live mode, and the wrapped empty-stack reset fuse SHALL no longer exist: an empty-stack read is a programmer error surfaced by the router, not a runtime re-home. Teardown SHALL remain the only event that replaces the whole stack; ordinary commits SHALL never pop or reset frames.

#### Scenario: Combat adoption resets to the combat root

- **WHEN** a valid committed snapshot switches the mode from exploration to combat while exploration submenus are open
- **THEN** the stack holds exactly the `combat.root` descriptor, the exploration frames and their focus keys are gone, and no exploration row remains activatable

#### Scenario: Transport loss leaves only the root frame

- **WHEN** the transport is lost while frames are open
- **THEN** the stack holds only the current mode's root descriptor and no stale activation can dispatch after reconnect without a fresh player action, with the stack non-empty at every observable moment after teardown

#### Scenario: Epoch reset leaves only the root frame

- **WHEN** a new transport generation retires the epoch and a fresh-epoch snapshot establishes the new one while submenus are open
- **THEN** the stack contains exactly one root descriptor for the new presentation before any player action

#### Scenario: No-puppet detach collapses the stack without a mode change

- **WHEN** a `no_puppet` protocol error detaches the character while exploration submenus are open and neither the mode nor the epoch changes
- **THEN** the stack collapses to exactly the single root descriptor and no open submenu row remains activatable

#### Scenario: Creation mode tears down to its root descriptor

- **WHEN** the presentation epoch resets while creation-mode frames are open
- **THEN** the stack holds exactly `creation.root` and no prior-frame payload can dispatch without a fresh player action

#### Scenario: Dialogue mode tears down to the dialogue root

- **WHEN** a valid committed snapshot switches the mode from exploration to dialogue while exploration submenus are
  open
- **THEN** the stack holds exactly the `dialogue.root` descriptor and no exploration row remains activatable
### Requirement: The resolver table completes with the services, combat, and creation families

The resolver table SHALL additionally implement, and produce the menus the migrated push sites produce today: services family (panel `services`) — `services.root` `{}`, `services.guild` `{}`, `services.board` `{}`, `services.quests` `{}`, `services.quest-detail` `{questIndex}`, `services.shop` `{}`, `services.stock` `{}`, `services.sell` `{}`, `services.confirm` `{questIndex}` (the abandon-confirmation frame derived from that quest row's server-authored confirm fields); combat family (panel `context_actions` combat form, selection state owned by the combat model) — `combat.root` `{}`, `combat.categories` `{}`, `combat.category` `{categoryIndex}`, `combat.group` `{categoryIndex, groupIndex}`, `combat.skill` `{skillKey}`, `combat.target` `{skillKey}`, `combat.forfeit` `{}`; creation family (panel `creation`) — `creation.root` `{}`, `creation.presets` `{}`, `creation.form` `{view: "custom" | "concept"}` resolving to the wizard's empty marker frame, `creation.confirm` `{kind, presetKey?}`. The table SHALL additionally implement the dialogue family (panel `dialogue`) — `dialogue.root` `{}` resolving to the single `對話選項` tab whose pane lists the committed `dialogue.choices` rows with their `explore.talk_scripted` payloads read from committed state at resolve time, and resolving to the shared unresolvable marker — carrying the panel's server-authored reason — when the committed panel is unavailable. An out-of-range index or absent key SHALL resolve to the shared unresolvable marker like a lost identity.

#### Scenario: Every completed-table source resolves from a live snapshot

- **WHEN** each newly added source is resolved against a committed snapshot of its owning mode with valid params
- **THEN** each returns the menu its migrated push site produced, with the same row keys, server-authored payloads, and titles

#### Scenario: A vanished quest degrades like a lost identity

- **WHEN** `services.quest-detail` resolves with a `questIndex` the committed services panel no longer lists
- **THEN** resolve returns the unresolvable marker, carrying the panel's server-authored reason when present

#### Scenario: The dialogue root resolves from committed state

- **WHEN** `dialogue.root` resolves against a committed snapshot whose `dialogue` panel is available
- **THEN** the pane rows carry the committed keyword identifiers and labels verbatim with payloads naming the
  committed host identity, and an unavailable panel resolves to the unresolvable marker with the panel's reason
