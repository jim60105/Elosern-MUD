# Affinity and Party Systems — Design

**Date:** 2026-08-08
**Status:** Approved
**Scope:** NPC-to-player affinity (好感度), AI-decided affinity deltas, NPC partying (組隊) with movement follow, joint combat, and quest assistance.

This document is a slice of the master design (`docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`,
§5.2 `relations` seam, §7.4 intent whitelist). Where this document conflicts with the master
design, the master design wins unless this document explicitly amends it.

---

## 1. Product Context

The player builds relationships with NPCs. Every NPC holds a hidden numeric affinity toward the
player (initial 0, natural cap 99). Affinity rises through ordinary interactions (conversation,
merchant trade, guild functions) and through partying with the NPC on quests. AI-facilitated
conversation lets the AI decide both the affinity gain for that exchange (0–10) and whether to
accept a party invitation, with the affinity value and cap supplied as judgment input. When the AI
is offline, a fixed affinity threshold decides invitation acceptance.

The numeric value is never shown to the player; it is presented as a seven-stage Traditional
Chinese ladder. Values above 99 (a future capability-break feature, not player-facing) map to the
topmost stage, which expresses devotion beyond reason.

The game is a fantasy JRPG-style setting (伊洛瑟恩大陸), not a wuxia setting; stage names use
Japanese-RPG flavor.

---

## 2. Architectural Decisions

| # | Decision | Rationale |
|---|---|---|
| A1 | **Affinity is stored per NPC, keyed by player.** `LivingEntity.relations` becomes a `RelationHandler` holding `{player_pk: record}`; the record stores `value`, `cap`, `daily_gain`, `daily_tick`. | Fills the seam declared in `typeclasses/entities.py` §5.2. Single-player means one entry per NPC in practice, but the keyed shape keeps the seam general. |
| A2 | **One write API.** `world/rules/affinity.py::apply_affinity_change(npc, player, source, delta)` is the sole affinity writer; negative deltas travel the same function (the future affinity-decrease path is built now, with no decrease events in this scope). | Preserves the single-writer invariant; decrease events become callers, not new writers. |
| A3 | **Natural cap 99 is a per-record `cap` field.** Special future events raise a record's `cap` (e.g. 150) to unlock three-digit values; the player UI never exposes the field, and the stage ladder covers it automatically via the topmost stage. | Cap-breaking is game design, not a display feature (per owner). |
| A4 | **Daily-gain cap resets lazily by comparing stored `daily_tick` to the current world day.** | Avoids touching the load-bearing clock settlement order in `world/rules/clock.py`; deterministic and cheap. |
| A5 | **Stage ladder and balance numbers live in `world/rules/rulebook/affinity.yaml`.** | Follows the D9 convention (balance numbers are data) and the rule-ID/test-ID pairing convention (D10 of the rules engine, §10 of master design). |
| A6 | **AI dialogue deltas use the existing `adjust_relation` intent** (whitelisted since `npc-dialogue`, currently forward-declared in `world/rules/npc_intents.py`), with a hard-bounded payload `delta: 0..10`. | Reuses the guarded dialogue pipeline and activates an existing seam. |
| A7 | **Party invitations travel the same npc_dialogue layer** via a new whitelisted intent `party_invite {accept: bool}`. | The invitation is a conversation; guardrail/retry/degrade are reused wholesale; speech flows naturally into chat memory. |
| A8 | **Offline fallback is a fixed threshold, not a stage boundary lookup.** `affinity >= 70` (the 羈絆 stage floor) decides acceptance when the AI layer degrades. The AI is never bound by the threshold. | Matches the owner's requirement: AI judges freely; the fixed value is only the offline fallback. |
| A9 | **Party membership: up to 4 NPCs per player; `world/rules/party.py` is the sole writer** of `player.db.party` (list of NPC dbids) and `npc.db.party_member` (player dbid). | One owner for membership lifecycle (join/leave/auto-leave). |
| A10 | **Bidirectional dismissal.** The player dismisses freely (no affinity cost); a future affinity-decrease event that drops affinity below the invite threshold triggers `leave_party(reason="affinity_below_threshold")`. The recheck hook is installed at the affinity write API now. | Owner requirement; the trigger is future work but the hook is built and tested now. |
| A11 | **Companions follow through the shared movement pipeline** (`world/rules/movement.py` / exit traversal) with no extra time cost; a failed move leaves the companion behind with a "跟丟了" message. | Follows the 13b idiom of one shared movement mechanism; no bespoke mover. |
| A12 | **Companions fight as allies in the existing player combat session**, acting through the existing `monster_behaviour` policy pipeline on the ally side, and never die: HP 0 knocks them out of the battle (nonlethal, per the guild-exam precedent). | NPCs are shared world entities; death must not be reachable. |
| A13 | **Quest assistance means companions contribute to the player's objectives** (kills count toward 討伐, presence counts toward location/escort/collect), and each then-in-party companion earns +2 affinity at quest turn-in via the quest-completion source, which is exempt from the daily cap. | Per owner decision: companions assist the player's quests; no per-NPC quest log. |
| A14 | **Quest turn-in affinity is written by `world/rules/affinity.py`; `world/quests/` only calls it.** | Affinity is rules-owned; quests is a named sibling deterministic package and may call the rules write API, but never writes affinity itself. |

---

## 3. Affinity System

### 3.1 Data model

```python
@dataclass
class AffinityRecord:
    value: int        # 0..cap; may exceed 99 only after a future cap break
    cap: int = 99     # natural cap; future events raise this per record
    daily_gain: int = 0
    daily_tick: int = 0   # world day at which daily_gain started accruing

class RelationHandler:
    def affinity_for(self, player) -> int
    def stage_for(self, player) -> AffinityStage
    def apply(self, player, source, delta) -> AffinityDeltaOutcome
```

`RelationHandler` lives in `world/rules/affinity.py` and is attached to `LivingEntity.relations`
replacing the `AttributeProperty(default=None)` placeholder seam. Storage is a single serialized
dict attribute on the NPC: `npc.db.relations_data = {str(player_pk): {...}}`.

`apply_affinity_change` is the **sole writer**. It:

1. Reads the record (or creates one at value 0, cap 99).
2. Resets `daily_gain` when `daily_tick != current_world_day`.
3. For capped sources, clamps the per-day gain at `DAILY_INTERACTION_CAP` (5) and refuses further
   positive deltas for that source class once the cap is reached. Sources: `talk`, `trade`,
   `guild`, `ai_dialogue` (capped); `quest_completion` (uncapped).
4. Clamps `value` to `[0, cap]`; negative deltas never clamp upward and never reset the daily cap.
5. After any negative delta, calls the party auto-leave recheck (A10) — a no-op while no decrease
   events exist.
6. Returns a structured outcome (applied, capped_this_day, delta_used) so callers can render
   player-facing feedback.

### 3.2 Stage ladder (`rulebook/affinity.yaml`)

```yaml
affinity:
  invite_threshold: 70
  daily_interaction_cap: 5
  quest_completion_gain: 2
  stages:
    - id: stage_fuxue_shijie_00
      floor: 0
      name: 初識
    - id: stage_shouxi_10
      floor: 10
      name: 熟識
    - id: stage_qinmu_30
      floor: 30
      name: 親睦
    - id: stage_xinlai_50
      floor: 50
      name: 信賴
    - id: stage_jibian_70
      floor: 70
      name: 羈絆
    - id: stage_zhi_ai_90
      floor: 90
      name: 至愛
    - id: stage_absolute_100
      floor: 100
      name: 絕對羈絆
```

The stage for value `v` is the last stage with `floor <= v`; stages are contiguous. The 100+
stage exists from day one but is unreachable while `cap = 99`; it is the topmost stage that a
future cap break feeds into. Player-facing glyphs use Traditional Chinese forms (信賴, 絕對).

### 3.3 Gains

| Source | Gain | Daily-capped | Call site |
|---|---|---|---|
| `talk` (deterministic keyword conversation) | +1 | yes | `commands/talk.py`, `explore.talk_scripted` |
| `trade` (successful buy or sell) | +1 | yes | `world/rules/economy.py` settlement |
| `guild` (registration, quest acceptance, rank exam) | +1 | yes | `world/rules/guild*.py` success paths |
| `ai_dialogue` (`adjust_relation` intent delta 0–10) | AI-chosen | yes | `world/rules/npc_intents.py` |
| `quest_completion` (each then-in-party companion) | +2 | no | quest turn-in path via `world/rules/affinity.py` |

AI freeform conversation receives **no fixed** +1; the AI's `adjust_relation` delta is the sole
gain for that exchange (no double counting). A single daily cap of 5 spans all capped sources.

### 3.4 Display

- `look <npc>` appends a stage line, e.g. 「她看著你的眼神裡帶著信賴。」 (per-stage authored
  flavor lines in the YAML).
- The numeric value is never rendered anywhere.
- No dedicated affinity-query command in this scope; `look` is the surface.

---

## 4. Party System

### 4.1 Membership

`world/rules/party.py` owns `join_party(npc, player)` and `leave_party(npc, player, reason)`:

- Storage: `player.db.party` = list of NPC dbids (max 4); `npc.db.party_member` = player dbid.
- `join_party` validates: target is an NPC, not already a companion, party not full (4), player
  and NPC present in the same room.
- `leave_party` is used by player dismissal (no affinity effect) and by the auto-leave recheck
  (reason `affinity_below_threshold`).
- Both are atomic and idempotent under re-application.

### 4.2 Invite command

`invite <npc> [訊息]` (aliases 邀請, 組隊), target resolution mirrors `commands/talk.py`:

1. Resolve the NPC; preflight the deterministic gate (not already companion, room not full).
2. Run the guarded `npc_dialogue` call with an extended prompt carrying `affinity`, `affinity_cap`,
   and `affinity_stage`, and with chat memory (the invitation is a conversation).
3. Parse the reply: speech always shown; `party_invite {accept: bool}` intent verified and applied
   through `join_party`; illegal intents discard only the intent, keep the speech (per §7.4).
4. Degradation: when the AI layer returns `None`, decide by `affinity >= invite_threshold` (70);
   the player sees the authored greeting or a deterministic accept/reject line.

The AI is never bound by the threshold: it may accept below 70 or reject above it. Only the
degraded path uses the threshold.

### 4.3 Dismissal and auto-leave

- `leave <npc>` (alias 解散) dismisses; no affinity change.
- The affinity write API (A2) runs the auto-leave recheck after every negative delta: if a record
  with an active party drops below `invite_threshold`, `leave_party(..., "affinity_below_threshold")`
  fires and the player is notified. No decrease events exist in this scope; the hook is covered by
  a direct unit test calling the write API with a negative delta.

### 4.4 Follow

- On player exit traversal (shared movement pipeline), every companion in the same room moves with
  the player at no extra time cost. If a companion cannot enter the destination (room rejects
  contents), it stays behind and the player sees a "跟丟了" line.
- Companions are not re-summoned automatically; re-entering their room restores the party state,
  which is persistent across disconnect/reconnect.

### 4.5 Joint combat

- When the player engages monsters, companions present in the room join the battlefield as allies.
- Companion turns use the existing `monster_behaviour` policy pipeline on the ally side and act
  through `ActionResolver`; targeting already supports the ally faction (`Relation.ALLY`).
- Companions cannot die: HP 0 applies the nonlethal knockout treatment (guild-exam precedent),
  removing them from the battle; recovery follows the normal clock-driven regen.
- Time settlement is unchanged (rounds × 6s at battle end).

### 4.6 Quest assistance

- While in party, companion actions contribute to the player's quest objectives: kills count
  toward 討伐 objectives, co-presence counts toward location/escort/collect objectives.
- At turn-in, each then-in-party companion earns +2 affinity (source `quest_completion`, uncapped),
  written exclusively through `world/rules/affinity.py`; `world/quests/` calls, never writes.

---

## 5. AI Layer Changes

### 5.1 Prompt context

`build_npc_dialogue_prompt` gains an optional `affinity_context` block injected into the user
payload: `{"affinity": 42, "affinity_cap": 99, "affinity_stage": "信賴"}`. The NPC sees the true
value (it must decide deltas and invitations); the player never sees it.

### 5.2 Intent changes

- `adjust_relation` — activated. Payload exactly `{delta: int}` with `0 <= delta <= 10`; the schema
  and the deterministic verifier both enforce the bound. Application goes through
  `apply_affinity_change(..., "ai_dialogue", delta)`; a capped-out daily budget rejects the delta
  (applied=False, speech kept).
- `party_invite` — new whitelisted kind. Payload exactly `{accept: bool}`. Application goes through
  `join_party`/nothing per `accept`, with the full deterministic re-verification (same room, not
  already companion, room not full).
- The degraded fallback for the dialogue layer is unchanged; `invite`'s own degradation is the
  threshold decision (A8).

---

## 6. Change Slicing

Six sequential per-day changes; each lands and verifies independently.

| # | Change | Depends on | Content |
|---|---|---|---|
| 1 | `affinity-system` | 3 (`entity-traits`), 6 (`rulebook`), 11 (`world-clock` day access) | `RelationHandler`, `rulebook/affinity.yaml` (stages + caps + thresholds), fixed gains + daily cap, talk/trade/guild hooks, `look` stage display, negative-delta path with the party recheck hook, unit tests per rule ID |
| 2 | `affinity-ai` | 1, 17 (`llm-client`), 19 (`npc-dialogue`) | Activate `adjust_relation` (schema + verifier + applier), inject affinity context into the dialogue prompt |
| 3 | `party-core` | 2 | `invite`/`leave` commands, `party_invite` intent, membership binding (max 4), offline threshold fallback, bidirectional dismissal with auto-leave hook |
| 4 | `party-follow` | 3, 13b (`movement-cost-charging`) | Companion follow through the shared movement pipeline, 跟丟了 handling |
| 5 | `party-combat` | 3, 9/10/16 combat session, 10b (`monster-behaviour`) | Ally-side battlefield entry, companion behavior policy, nonlethal knockout |
| 6 | `party-quest` | 3, 15 (`quest-runtime`), 16 (`guild-economy` turn-in) | Objective contribution by companions, +2 turn-in affinity per companion |

---

## 7. Testing Strategy

| Area | Method |
|---|---|
| Rulebook rules | One test per rule ID in `rulebook/affinity.yaml`, names mirror rule IDs (project convention) |
| Affinity logic | Pure `unittest.TestCase` for cap/daily-reset/stage mapping (lazy tick); `EvenniaTest` for NPC-record persistence and look display |
| AI deltas and invites | `FakeLLMClient` replays: accept, reject, delta in range, delta out of range rejected, degraded threshold fallback |
| Guardrail | Malformed/out-of-range `adjust_relation` and `party_invite` payloads leave the DB untouched |
| Auto-leave hook | Negative delta below threshold through the write API ends the party and notifies |
| Offline playability | All LLM profiles fail; full loop invite → follow → combat → quest turn-in → +2 affinity → dismiss completes |
| Command surface | `docs/game/commands.md`, `docs/game/command-reference.md`, `tests/test_command_docs.py` updated for `invite`/`leave` |

---

## 8. Open Questions Carried Forward

- None blocking. Decrease events, cap breaks, and multi-companion AI dialogue are deliberately
  deferred seams, each with an explicit hook built and tested now.
