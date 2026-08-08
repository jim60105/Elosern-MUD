# party-combat

## Why

Companions follow the player (`party-follow`), but combat ignores them: `engage` records only the
player on the allied side, and the battlefield machinery's two-team model (`party` vs `foes`),
the team-relative `monster_behaviour_policy`, and the allied-faction targeting already anticipate
multi-member sides. This change makes companionship matter in battle — companions join
engagements as allies, act through the deterministic behavior policy, and can never die
(per-entity nonlethal knockout), keeping NPCs safe as shared world entities.

## What Changes

- **Companions join engagements.** `engage <target>` includes every co-located, living, bound
  companion in the session's allied team (`player_ids`); the battlefield's two-team model,
  team-relative `relation_to`, and ALLY faction targeting then apply to companions with no
  separate machinery.
- **Companions act through the deterministic policy.** The session's non-player action provider
  (already team-relative) supplies one policy request per companion per round — the same
  `monster_behaviour_policy` pipeline that drives monsters, selecting targets from the opposing
  team. Companions never act on the player's turn and never consume the player's queued request.
- **Companions cannot die.** The nonlethal policy becomes per-entity: the combat context carries
  `nonlethal_keys` (companion keys in hostile sessions; the exam's session-wide flag is
  unchanged). A lethal crossing on a companion floors HP at 1 and emits `target_knocked_out`
  instead of `target_defeated`, so no kill credit, XP, or DEFEAT progress observes a companion
  death. Knocked-out companions remain bound and recover through normal clock-driven regen.
- **Session terminal rules are player-centric.** The session ends on player defeat, all foes
  defeated/fled, flee, or forfeit — a knocked-out companion does not end it, and the player's
  defeat ends it even if companions survive. Settlement, flee, forfeit, and skip-safety behavior
  are unchanged.
- **No new commands or UI.** `engage`, `cast`, `combat forfeit`, and the existing webclient
  combat menu are unchanged in surface; companion participation is visible through the existing
  battlefield roster.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `party-system`: The membership capability gains the combat requirement — allied participation
  in the player's combat session, policy-driven companion turns, per-entity nonlethal knockout,
  and player-centric terminal rules.
- `player-combat-session`: The `engage` requirement changes (co-located living bound companions
  join the allied team) and the round requirement changes (non-player participants — monsters and
  companions alike — receive deterministic policy requests).
- `action-resolution-pipeline`: The nonlethal policy requirement changes — the context MAY carry
  per-entity `nonlethal_keys` alongside the session-wide flag, and knockout projection consults
  the key set.

## Impact

- **New code**: companion-resolution helpers in `world/rules/party.py`, `world/rules/tests/`
  combat-party test modules.
- **Modified**: `world/rules/combat_session.py` (`engage` participant collection, the non-player
  action provider, per-entity nonlethal context), `world/rules/combat.py` /
  `world/rules/action.py` (per-entity nonlethal projection and knockout emission), and the three
  delta specs.
- **Dependencies**: `party-core` (binding), `party-follow` (co-location), `player-combat-session`,
  `monster-behaviour` (the policy pipeline), `action-resolution-pipeline` (the nonlethal policy).
- **Out of scope**: quest assistance and the +2 completion bonus (`party-quest`), companion
  equipment/skills UI, multi-companion AI dialogue, companion death or perma-loss mechanics.
