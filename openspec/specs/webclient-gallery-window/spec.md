# webclient-gallery-window Specification

## Purpose
Compose the gallery as its own book-style window: a category rail, the subject
wall and the image page over the committed `gallery` panel, with every
mutation sent through the application's single dispatch entry.

## Requirements

### Requirement: The rail switches category through the server
The window SHALL render one rail tab per committed category in order, with its client label. Pressing an enabled tab other than the committed `category` SHALL send exactly one `gallery.category.select` and mark that tab pressed until the next committed panel; the wall SHALL keep showing committed groups until then. A disabled tab SHALL stay focusable, expose its committed reason and send nothing.

#### Scenario: The pressed tab is marked before the commit
- **WHEN** the player presses the 魔物 tab while `mine` is committed
- **THEN** one `gallery.category.select` with `monster` is sent, the 魔物 tab is marked pressed, and the wall still shows the `mine` subjects until a panel with `category: "monster"` commits

#### Scenario: A disabled tab sends nothing
- **WHEN** the player activates the disabled 人物 tab
- **THEN** no action is sent and its committed reason is exposed to assistive technology

### Requirement: Footer presses map to one action or one editor
Each footer key SHALL map to exactly one dispatch or editor: 刪除 to `gallery.card.delete`, 設為預設 to `gallery.default.set` or `gallery.official.select`, 清除選取 to `gallery.official.clear_selection`, 清除個人調整 to `gallery.official.geometry.clear`, and 臉框, 舞台位置, 綁定裝備, 生成新圖 and 重新生成 to their existing editors. Every send SHALL respect the connected, locked and one-in-flight gates and carry the committed subject key.

#### Scenario: Setting the default sends one action
- **WHEN** the player presses 設為預設 on a stored card
- **THEN** exactly one `gallery.default.set` with the committed subject key and that card's `image_id` is sent

#### Scenario: A locked window sends nothing
- **WHEN** a mutation is in flight and the player presses 設為預設
- **THEN** no second action is sent

#### Scenario: Regenerate opens the generate editor
- **WHEN** the player presses 重新生成 on a one-card subject
- **THEN** the generate drawer opens for that subject and nothing is sent until it is submitted

### Requirement: Image selection is client-local and follows the committed subject
When the committed `selected` subject changes, the window SHALL select that subject's default card, else its first card row, else its current official entry, else its first official entry, else the empty page. A selected image that a newer panel no longer lists SHALL be replaced by the same rule and any editor drafted against it SHALL close without sending.

#### Scenario: A new subject opens on its default card
- **WHEN** a panel commits a new `selected` whose second card is the default
- **THEN** the page shows that default card

#### Scenario: A vanished image closes its editor
- **WHEN** the face-rect modal is open for a card that the next committed panel no longer lists
- **THEN** the modal closes without sending and the page shows the replacement selection

### Requirement: Focus is rescued and Escape closes in layers
A committed panel that removes the focused wall tile SHALL move focus to the rail's selected tab. Escape inside the tray SHALL return to the owner tile; a further Escape SHALL close the window and restore focus to its opener.

#### Scenario: Escape twice from the tray closes the window
- **WHEN** focus is in the tray and the player presses Escape twice
- **THEN** the first press focuses the owner tile and the second closes the window
