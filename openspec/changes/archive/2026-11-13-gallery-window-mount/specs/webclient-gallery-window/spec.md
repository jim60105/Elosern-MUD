## ADDED Requirements

### Requirement: The 圖庫 tool opens the gallery window
The 圖庫 tool SHALL open the gallery window as a drawer-keyed window outside the overlay host, closing any open overlay or drawer first, and closing it SHALL restore focus to the tool. While the window is open and the committed panel becomes unavailable, the window SHALL show the committed reason and lock every control.

#### Scenario: Opening from the tool and closing restores focus
- **WHEN** the player activates the 圖庫 tool and then presses Escape on the wall
- **THEN** the gallery window opened under the `gallery` drawer key, no overlay host rendered it, and focus returned to the 圖庫 tool

#### Scenario: An unavailable panel locks the open window
- **WHEN** the window is open and a committed revision makes the `gallery` panel unavailable
- **THEN** the window shows the committed reason and no gallery action can be sent
