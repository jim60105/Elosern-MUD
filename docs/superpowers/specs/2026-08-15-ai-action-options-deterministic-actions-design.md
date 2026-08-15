# AI Action Options — Deterministic Available Actions

**Date:** 2026-08-15
**Status:** Approved
**Scope:** The `context_actions` panel kinds `exploration` and `dialogue` — deterministic producers
that always compute the currently-valid action list from registries and room state, plus the
`default_cards()` derivation that fills `suggestions` when the AI layer degrades.

Part of the [AI Action Options document set](2026-08-15-ai-action-options-overview-design.md).
These producers are read-only: they consume canonical handlers, components, and registries and
never write state. They are also the vocabulary source — the `ACTION_CODE_ALLOWLIST` of the schema
(schema doc §3.1) is their emitted union, which makes the AI proposals *capable* by construction
of anything the rules allow.

---

## 1. Producer Architecture

- New presenters registered in `web/webclient/presentation/registry.py` under `context_actions`
  for kinds `exploration` and `dialogue`; the combat presenter is untouched (its schema v2 payload
  shape stays byte-identical for combat sessions).
- Both producers reuse the affordance builders already owned by `web/webclient/presentation/exploration.py`
  — the same `move` / `look` / `interact` composition that feeds the exploration panel v1 — rather
  than duplicating rule reads. Where a builder lives inside a panel module, it is extracted as a
  public helper and re-imported, keeping one rule-reading code path (the project's repeated
  "no duplicated rule logic" invariant).
- Every emitted entry carries the real dispatcher `action_id` and a player-facing label; navigation
  affordances keep the `surface` shape (`guild` / `shop`).

---

## 2. Exploration Kind — Rule Table

Derived per room visit; each rule reads registries/components only:

| Situation | Emitted actions | Source |
|---|---|---|
| Exits present | `explore.move` per exit (bounded, `exit_ref` param) | room exit registry |
| Present room objects | `explore.look` + per-object `interact` (bounded, `target_id`) | room contents view |
| Present NPC | `explore.talk_scripted` (keyword from host table) / `explore.talk_freeform` (LLM NPC) / `explore.engage` for reachable NPCs | dialogue key lookup (`world/rules/dialogue.py`) + `interaction_reason(npc, "talk")` gate |
| Present monster | `explore.engage` (`monster_id`), skipped when a persistent combat session owns the room | monster presence view |
| Quest objective NPC present | Objective-relevant actions ranked first (§4) | quest progress public view |
| Idle baseline | `explore.look`, `explore.wait`, plus `map` / `guild` / `shop` navigation surfaces as available | stable baseline, always emitted |

The `interaction_reason` schedule gate is applied identically to the adapters: a schedule-blocked
NPC emits no talk/engage card, so a card the player can click is never one the adapter would reject
with `schedule_blocked`.

---

## 3. Dialogue Kind — Rule Table

Emitted while a dialogue host is the current conversation partner:

| Host type | Emitted actions |
|---|---|
| Scripted host (`ScriptedDialogue` / onboarding guide) | `explore.talk_scripted` per keyword of the host's `DIALOGUE_TABLE` responses (bounded, 3–5 by curation rule), then `explore.look` and `explore.move` (abandoning the conversation is always available) |
| LLM NPC (`LLMNPC`) | No deterministic freeform (the rules cannot invent speech); degraded dialogue suggestions are *empty* by design — the panel shows only the honest entry point (`explore.talk_freeform` with an empty opening, rendered as a plain "開口交談" affordance) plus navigation |
| No host | Kind does not apply; the producer emits nothing and the panel falls back to exploration kind |

The honest-empty rule is deliberate: a deterministic fake opening line would factory-produce
stilted dialogue and would leak as obviously templated content (schema doc placeholder gate).

---

## 4. `default_cards()` — the degraded suggestions

One shared derivation used by the trigger service when the AI is absent (fingerprint floor,
trigger-service doc §3.5) and by the client the moment `degraded` shows:

1. Take the current kind's emitted actions in rule-table order.
2. Curate to 3–5 entries: objective-relevant first, then interact/talk over navigation, then
   baseline `look`/`wait`; navigation surfaces never outrank action cards.
3. Each entry is already a `SuggestionCard`-compatible shape (kind `known_action` with exact
   `action_id` + params) — the only difference from an AI card is the producer.

Because both the AI prompt and the degraded path derive from the same affordance list, a player
who sees AI cards and a player who sees rule cards are acting in the same action space — no card
teaches an action shape the rules cannot execute.

---

## 5. Degrade Agreement Contract

The degraded suggestions must never *disagree* with the full kind list: `default_cards()`
⊆ kind list, same params, same labels. Enforced by a pure test that runs both derivations across
the scenario fixtures and asserts subset semantics — the deterministic guarantee that "AI 掛掉時
玩家看到的就是規則清單" holds without exception.

---

## 6. Tests

| Area | Method |
|---|---|
| Rule table | Per-scenario fixtures: empty room, room with exits, NPC talk gate (schedule blocked), monster present, quest objective, dialogue host table keywords |
| `default_cards()` | Curiosity cap 3–5; objective first; navigation never outranks; subset ⊆ kind list on every fixture |
| Vocabulary union | Emitted union == accepted `ACTION_CODE_ALLOWLIST` (one pure parity test) |
| Registry | `context_actions` panel serves combat / exploration / dialogue kinds without collision; combat payload byte-stable |
| Read-only | Producers never call a mutator (asserted by the existing deterministic-path test scanning) |

---

## 7. Open Questions Carried Forward

- Whether proximity-aware `engage` cards should surface for guarded NPCs (e.g. guild examinators)
  once guard interaction rules land — the affordance builder seam already isolates the rule table.