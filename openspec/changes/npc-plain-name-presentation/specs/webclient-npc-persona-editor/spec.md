# Spec Delta

## MODIFIED Requirements

### Requirement: The author editor opens from the selected target and binds to it
Activating a target's 編輯人物設定 navigation SHALL open one editor window bound to that target identity and the presentation epoch current at opening, SHALL immediately request `npc.persona.read` for that identity, and SHALL never rebind to a target selected afterwards. Only one editor SHALL be open at a time, and opening it SHALL not dispatch any other action.

#### Scenario: The entry opens a bound editor and reads once
- **WHEN** the player selects a present NPC, opens its verb menu, and activates 編輯人物設定
- **THEN** one editor opens in the loading state, exactly one `npc.persona.read` naming that NPC is dispatched, and selecting a different target afterwards does not change the editor's bound NPC

#### Scenario: A disabled entry explains itself
- **WHEN** the target's 編輯人物設定 entry is disabled by the server
- **THEN** activating it opens nothing and the server-authored reason is shown

#### Scenario: The editor reuses existing shell primitives
- **WHEN** the editor is built
- **THEN** it reuses the client's existing drawer frame, header, overlay, typography, spacing, and focus primitives
- **AND** no full-screen NPC catalogue or new layout system is added

#### Scenario: Header contains no independent NPC title
- **WHEN** the selected NPC editor opens
- **THEN** the header shows the plain name and the private read result contains no npc_title field
