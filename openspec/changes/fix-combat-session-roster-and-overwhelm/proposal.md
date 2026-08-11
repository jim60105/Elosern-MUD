## Why

Two combat-session issues from audit run-1, one fix and one design clarification: (F07) terminal settlement passes only `[actor]` to the clock, so companions (and the exam opponent) get no gauge regen and knocked-out companions stay at the HP-1 floor, excluded from later engagements; (F09) the overwhelm design intent is clarified — compression resolves only when the **player's** team is overwhelming, and foe-overwhelming encounters deliberately play out round-by-round so the player keeps agency (skills, flee) and is never forced into an unavoidable compressed defeat.

## What Changes

- Terminal combat settlement scopes the clock advance to the living, non-fled battlefield roster, so every participant regenerates for the accumulated combat seconds.
- Overwhelm compression remains single-direction: it SHALL run only when the player's team is the overwhelming side. A foe-overwhelming verdict is informational only; the session never invokes the compressed resolver for it, and the player retains full per-round agency until defeat or flee.

## Capabilities

### Modified Capabilities

- `player-combat-session`: settlement entity scope; overwhelm dispatch scope clarified to player-direction only.
- `party-system`: companions recover through combat settlement.
- `single-shot-resolution`: reverse-overwhelm equivalence contract removed; compression is player-direction only.

## Impact

- `world/rules/combat_session.py` (`settle_session`, `submit_player_action`), `world/rules/overwhelm.py` (unchanged logic; classifier output for the foe direction is no longer a dispatch input), party and overwhelm tests; spec text updates.
