## 1. Settlement roster scope

- [ ] 1.1 In `world/rules/combat_session.py::settle_session`, build the living, non-fled roster scope and pass it to `settle_combat_result`; keep `[actor]` only when the roster is unavailable
- [ ] 1.2 Confirm exam-mode temporary opponent deletion still runs after settlement

## 2. Overwhelm direction scope (design clarification)

- [ ] 2.1 Keep compression gated on `overwhelming == player_team`; add an explicit guard and comment documenting that foe-overwhelming and contested verdicts never dispatch the resolver
- [ ] 2.2 Confirm `overwhelming_team` remains informational in session outputs; no behavior change to the player-overwhelming path
- [ ] 2.3 Update the `single-shot-resolution` spec text (reverse-equivalence contract removed) and any tests referencing reverse overwhelm dispatch

## 3. Tests and verification

- [ ] 3.1 Test: terminal settlement regenerates companion gauges; a knocked-out companion rises above 1 HP and can re-engage
- [ ] 3.2 Test: foe-overwhelming session plays one ordinary round per submission and never calls the resolver (flee and re-choice remain available); player-overwhelming behavior unchanged
- [ ] 3.3 Run combat-session, party, overwhelm, and world-clock tests
