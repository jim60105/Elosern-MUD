## ADDED Requirements

### Requirement: Undeclared card operations reject with stable codes
A gallery mutation adapter SHALL map the writer's refusal of an undeclared operation to a stable code with a bounded zh-TW message: `face_rect_unsupported` for face-rectangle updates and official face-rectangle overrides, `stage_unsupported` for stage updates and official stage overrides, and `delete_unsupported` for card deletion. The rejection SHALL publish the standard gallery refresh.

#### Scenario: Deleting a card of a kind without deletion is refused
- **WHEN** `gallery.card.delete` names an existing card of a kind declaring `supports_card_delete` false
- **THEN** the result is `rejected` with `delete_unsupported`, the card is unchanged, and one update refreshes gallery, art and roster

#### Scenario: A stage update on a kind without stage is refused
- **WHEN** `gallery.stage.update` names a card of a kind patched to declare `supports_stage` false
- **THEN** the result is `rejected` with `stage_unsupported` and the stored stage is unchanged
