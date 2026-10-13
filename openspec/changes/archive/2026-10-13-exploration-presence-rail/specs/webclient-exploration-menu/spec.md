## REMOVED Requirements

### Requirement: The keyboard-first exploration dock roots at the scene overview and opens dialogue directly
**Reason**: The 人物 and 物件 rows and the target's verb popover leave the command panel for the presence rail and the centred verb card. The root requirement is restated, with every scenario that still holds, as "The exploration dock roots at the compass and the presence rail and keeps the footer overview" in `webclient-presence-rail`.
**Migration**: Scenarios about the 出口 row moved to `webclient-exit-compass` in `exploration-exit-compass`. Scenarios about the 人物 row, the 物件 row, the verb popover, and the popover's rows moved to `webclient-presence-rail` as rail and verb-card scenarios. The footer, child-frame, navigation, mode-change, and keyboard-router scenarios carry over unchanged in the new requirement until `exploration-room-actions` retires the footer.
