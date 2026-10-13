## REMOVED Requirements

### Requirement: The exploration dock roots at the compass and the presence rail and keeps the footer overview
**Reason**: The footer, the wait frame, and the suggestions frame are retired, and the exploration root is restated in `webclient-room-actions` ("The exploration screen roots at the compass, the rail, and room actions").
**Migration**: The footer scenarios moved to `webclient-room-actions` (the place-card 查看房間 and 等待 buttons and the 建議 pill); the child-frame scenarios became the wait card and suggestions card scenarios there; the remaining scenarios are covered by its empty-root and mode-change scenarios.
