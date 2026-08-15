# AI Action Options — Deterministic Available Actions

**Date:** 2026-08-15
**Status:** Approved (revised after rubber-duck review)
**Scope:** The canonical affordance contract — the shared current-valid-action list that fills
`context_actions` kind `exploration`, feeds `default_cards()`, and is the exclusive vocabulary of
AI proposals. This revision drops the separate `dialogue` kind for v1 (overview D-6) and excludes
navigation surfaces from suggestions.

Part of the [AI Action Options document set](2026-08-15-ai-action-options-overview-design.md).
These producers are read-only: they consume canonical handlers, components, and registries and
never write state. They are also the vocabulary source — the schema ladder's stage 9 requires an
exact `(action_code, params)` match against the emitted affordances
([schema](2026-08-15-ai-action-options-schema-design.md) §3.1).

---

## 1. Canonical Affordance Contract

One public module owns the affordance shape: `web/webclient/presentation/affordances.py`
(extracted from the builders embedded in `web/webclient/presentation/exploration.py`, so one
rule-reading code path serves both the exploration panel v1 and the new layer):

```
Affordance {
  action_id: str               # real dispatcher id (see the exact table below)
  label: str                   # player-facing label (the same text the dock shows)
  params: Mapping[str, str | int]   # produced by the action's OWN validator (wire-shape guarantee)
  freeform: bool               # true for the talk opener entry (bound next to params)
  navigation: bool             # surfaces (map/guild/shop) — never eligible for suggestions
}
```

`ACTION_CODE_ALLOWLIST` (schema doc stage-9 vocabulary) is the emitted `action_id` union of this
module, asserted by one pure parity test. Navigation affordances carry `navigation: true` and are
*excluded from suggestions* by construction (review R6): they have no dispatcher action code, so a
suggestion card could never execute them; they remain in the full `context_actions` kind list that
the dock renders as surface-openers.

### 1.1 Exact action shapes (wire-shape guarantee)

Every params dict below is produced by calling the registered validator itself on a candid dict —
the affordance builder returns the **normalized validator output**, so the card shipped to the
client is byte-for-byte the payload the dispatcher accepts (review R13). This replaces any
"presentation-shaped" guesswork: there is exactly one payload contract per action, the validator's.

| action_id | params (validator-normalized) | Validator |
|---|---|---|
| `explore.move` | `{"exit_ref": str, "current_node": str}` | `validate_move_payload` |
| `explore.look` | `{"room": true}` (room survey) or `{"target_id": int}` (targeted) | `validate_look_payload` |
| `explore.talk_scripted` | `{"npc_id": int, "keyword_id": str}` | `validate_talk_scripted_payload` |
| `explore.talk_freeform` | `{"npc_id": int}` on the card; client appends `speech: label` at dispatch | `validate_talk_freeform_payload` |
| `explore.engage` | `{"monster_id": int}` | `validate_engage_payload` |
| `explore.wait` | `{"daypart": str}` (fixed form) | `validate_wait_payload` |

There is **no `explore.interact` action** in the production registry — the exploration panel's
`interact` group is a label over per-target affordances, not an action. Suggestions therefore
never carry `interact`; interacting with a room object is a targeted `explore.look` card
(schema doc stage-9 canonical match keeps the two consistent).

Extraction rule: the exploration panel v1 presenter keeps emitting byte-identical payloads while
delegating to the shared builders. No behavior change outside the new feature.

---

## 2. Exploration Kind — Rule Table

Derived per room visit; each rule reads registries/components only:

| Situation | Emitted affordances | Source |
|---|---|---|
| Exits present | `explore.move` per exit, params `{exit_ref, current_node}` | room exit registry + `_current_node` |
| Present room objects | `explore.look` per object, params `{target_id}` (the panel's `interact` group is a label, not an action — §1.1) | room contents view |
| Present NPC | `explore.talk_scripted` (`{npc_id, keyword_id}` per host table keyword) / `explore.talk_freeform` (`{npc_id}`, the conversation opener) / `explore.engage` for reachable NPCs | dialogue key lookup (`world/rules/dialogue.py`) + `interaction_reason(npc, "talk")` gate |
| Present monster | `explore.engage` (`{monster_id}`), skipped when a persistent combat session owns the room | monster presence view |
| Quest objective NPC present | Objective-relevant affordances ranked first (§4) | quest progress public view |
| Idle baseline | `explore.look` (`{room: true}`), `explore.wait` (`{daypart}`) | stable baseline, always emitted |
| Navigation | `map` / `guild` / `shop` surfaces (kind-list only, never suggestions) | surface availability |

The `interaction_reason` schedule gate is applied identically to the adapters: a schedule-blocked
NPC emits no talk/engage affordance, so a card the player can click is never one the adapter would
reject with `schedule_blocked`. Companion guard: engagement affordances gate on `interaction_reason`
for their own action kind, mirroring `_engage_adapter`.

### 2.1 Conversation entry (v1 replaces the dialogue kind)

There is no persistent dialogue session in the codebase, so "current conversation partner" is not
derivable from canonical state (rubber-duck Q4). v1 therefore has **no `dialogue` kind**: the
present-table already emits `talk_scripted` keyword cards and a bound `talk_freeform` entry; a
conversation is steered by those cards and by the existing freeform drawer, exactly as the adapters
already support. The `context_kind` enum stays closed at one value (`exploration`), removing the
provenance problem and the degraded-empty-card contradiction together (rubber-duck R5).

---

## 3. `default_cards()` — the degraded suggestions

One shared derivation used by the trigger service when the AI is absent (fingerprint floor,
trigger-service doc §3.4) and by the presenter when `options_state.status == degraded`:

1. Take the current kind's affordances in rule-table order, **excluding `navigation` entries and
   freeform entries that cannot bind a present target** (post-gate, so a schedule-blocked NPC is
   already gone).
2. Curate to 3–5 entries: objective-relevant first, then talk/interact over baseline, then
   `look`/`wait`; a `talk_freeform` entry may appear once as the conversation opener
   (确定性無法發明台詞，所以 freeform 只以「開口交談」入口卡出現，不假造內容).
3. Each entry is already an executable suggestion card: `known_action` (or freeform with target),
   same `action_id`, same typed params, same label as the dock shows.

Changed bound: `degraded` cards are the curated subset in 0–5 (a room with nothing actionable —
no exits, no NPCs, no monsters, no objects — degrades to 0 with the section hidden); the 3–5
minimum applies to AI `ready` proposals only. The subset contract holds: `default_cards()`
⊆ kind list, same params, same labels — asserted by the subset test, so "AI 掛掉時玩家看到的就是
規則清單" holds without exception (rubber-duck R5 dead-end fix: with dialogue kind gone, the
baseline cards always cover the empty room case where meaningful).

---

## 4. Rank Order and Canonical Replacement

Both the AI prompt and `default_cards()` consume the same rank order: objective-relevant →
talk/interact → baseline `look`/`wait`. For AI proposals the canonical replacement happens in the
schema ladder stage 9 — the model's params are discarded and replaced by the matching affordance's
payload — so prompt and ladder cannot disagree.

---

## 5. Tests

| Area | Method |
|---|---|
| Rule table | Per-scenario fixtures: empty room, room with exits, NPC talk gate (schedule blocked), monster present, quest objective, multi-LLM-NPC binding |
| `default_cards()` | Curated 0–5; objective first; navigation never included; subset ⊆ kind list on every fixture |
| Vocabulary | Emitted `action_id` union == accepted stage-9 vocabulary (one pure parity test) |
| Canonical payload | Model-typed params replaced; a valid-now card executes against the real adapter in an integration test |
| Read-only | Producers never call a mutator (asserted by the existing deterministic-path test scanning) |
| Panel stability | Exploration panel v1 payload byte-identical after the extraction refactor |

---

## 6. Open Questions Carried Forward

- Whether proximity-aware `engage` cards for guard NPCs surface once guard interaction rules land —
  the affordance builder seam already isolates the rule table.
- Whether a later dialogue session system (persistent conversation state) reintroduces a `dialogue`
  kind — the closed enum can grow with its own provenance rule.