# Spec Delta

## REMOVED Requirements

### Requirement: The character-status drawer degrades section by section and never substitutes a disguise
**Reason**: `CharacterStatusDrawer` is deleted; the party window's 狀態 tab presents the viewed member's status from the `character` panel, which is available in every mode.
**Migration**: See `webclient-party-window` requirements "The status tab shows true values with a trait waterfall" and "The status tab shows conditions and an honest disguise".
