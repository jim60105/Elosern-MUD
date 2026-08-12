## Context

`settle_session` passes only `[actor]` to `settle_combat_result` (`world/rules/combat_session.py:868-871`), so `_settle_gauge_regen` (`world/rules/clock.py:112-133`) never regenerates companions or the exam opponent. Separately, `submit_player_action` gates compression on `overwhelming == player_team` (`combat_session.py:735-736`); `classify_overwhelm` (`world/rules/overwhelm.py:210-224`) can return the foe team, but that verdict is now a deliberate design signal, not a dispatch input.

## Goals / Non-Goals

**Goals:**
- Combat settlement regenerates every living roster member.
- Overwhelm compression is player-direction only; foe-overwhelming fights stay round-by-round so the player can always act or flee — no unavoidable compressed defeat.

**Non-Goals:**
- Changing gauge math, overwhelm classification thresholds, or the resolver's internals (it stays direction-agnostic; the session just never calls it for the foe direction).
- Companion regen on non-combat clock calls (movement/skip keep their documented scopes).

## Decisions

**D1 — Settlement scope = living, non-fled roster.** In `settle_session`, build `participants = [entity for key, entity in battlefield.roster.items() if key not in battlefield.fled and stored_hp(entity) > 0]` and pass it to `settle_combat_result`. When the roster is unavailable (recovery fallback) or holds no living non-fled member, `[actor]` is used only while the actor's stored HP is above 0 — so a solo flee keeps its historical actor regen, but a defeated player at 0 HP is never revived by settlement (kill semantics; only the world clock advances).

**D2 — Compression dispatch stays player-direction only; document it.** The existing gate `if overwhelming == player_team:` is the intended contract. The change adds an explicit guard/comment and spec coverage that a foe-overwhelming verdict (or a contested verdict) never dispatches `resolve_overwhelm`; the informational `overwhelming_team` value may still be reported to the UI.

**D3 — Spec alignment.** The `single-shot-resolution` reverse-overwhelm equivalence contract is removed (the resolver math is unchanged; the production dispatch simply never exercises the reverse direction).

## Risks / Trade-offs

- **Roster regen for dead foes**: excluded via HP>0; a foe already at 0 HP is skipped (matches kill semantics).
- **Exam opponents**: now regenerated too — harmless, and the temporary opponent is deleted right after settlement.
- **Player-overwhelming fights unchanged**: only the clarified dispatch scope and tests change for the player side.
- **Landing order**: applies after `fix-combat-settlement-recovery` (the outer round transaction owns the `submit_player_action`/`settle_session` seams this change edits).
