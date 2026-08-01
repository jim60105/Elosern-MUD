# Player Onboarding Flow — Design

**Date:** 2026-08-02
**Status:** Approved
**Scope:** The full first-session journey: connection screen, world introduction, character-creation
UX, activation arrival, a scripted arrival scene, guard guide dialogue, and the transition into the
existing deterministic first-day arc.

This is a superpowers spec, not an OpenSpec artifact. It is the source of truth for the OpenSpec
changes listed in §8; when an OpenSpec change conflicts with this document, this document wins.

---

## 1. Product Context

The deterministic milestone already yields a playable game: account registration auto-creates a
player shell marked `creation_pending`, the `character` command offers preset and custom creation,
and activation unlocks normal gameplay. But the first-session experience is currently blank: Evennia's
default connection screen, a bare prompt-based creation wizard, and the freshly activated character
left standing in `Limbo` with no introduction, no guidance, and no first event.

This spec designs the complete first-session journey. It must remain fully deterministic and
offline-playable: no LLM and no image-generation service may be required at any point.

Content constraints carry over unchanged: every character is an adult (`age >= 18` and
`apparent_age >= 18`); player-facing prose is Traditional Chinese; lore terms follow the canonical
registry spellings.

---

## 2. Design Decisions

| # | Decision | Rationale |
|---|---|---|
| O1 | **Full-journey scope**: connection screen → world intro → character creation → activation arrival → guard guide → existing first-day arc. | The blank Evennia shell is the product's front door; every stage of it needs authorship. |
| O2 | **Activation moves the character** to the South Gate of 聖潔王都 (`capital_altoria`, `(2,0)`). Amends `player-character-creation`'s "activation does not move" clause. | The player's first sight should be the capital, not a gray waiting room. |
| O3 | **Scripted beat engine** authored as immutable data under `world/onboarding/`. | Mirrors the project's data-driven conventions (quest catalog, lore registries); testable beat-by-beat; reusable for future scripted scenes. |
| O4 | **A dedicated guard NPC** at the South Gate carries an `OnboardingGuide` component and a keyword→response dialogue table. | Teaches `look`, movement, and NPC interaction as the first guided beats. The component name encodes intent (onboarding), not the NPC's future role — a guard may gain other, non-onboarding dialogue later. |
| O5 | **Deterministic only. No LLM dependency.** | Acceptance criterion of the milestone; the guide must work with every LLM service offline. |
| O6 | **Single `onboarded` flag** plus separately tracked guide progress. | Matches the "replay arrival on reconnect, never repeat a line twice" requirement with minimal state. |
| O7 | **Skip is always possible.** `onboarded` is set on first hunt turn-in; skipping the guide only records "guide skipped". | The player may walk away at any time; no forced handholding, and the tutorial stays reachable afterwards. |
| O8 | **Onboarding state writes route through `world/rules/onboarding.py`.** No new writer package. | Preserves the single-writer invariant; no design-doc §3.1 amendment is needed. |

---

## 3. Player Journey (beat by beat)

Target duration: **5–8 minutes** excluding the first hunt combat.

### Beat 0 — Connection screen
Custom `CONNECTION_SCREEN_MODULE` with a title banner, a one-line premise, and login/registration
prompts (CONNECT / CREATE).

### Beat 1 — Post-login introduction
After registration or login, a short world introduction (2–3 lines) is shown before character creation.

### Beat 2 — Character creation (restyled `character` command)
The command keeps its existing preset/custom logic. Its output gains:
- a world-view framing line ("你站在伊洛瑟恩大陸的門口…"),
- preset previews: one-line race description, allocation emphasis, one-line background,
- explanatory prompts in custom mode (what each race and allocation means).

### Beat 3 — Activation arrival
On successful activation the character is teleported to the South Gate and receives a welcome
message ("歡迎，艾琳。你踏上了伊洛瑟恩大陸的土地。"). The world clock stays at tick 0 (it only
advances on player action).

### Beat 4 — Arrival scene (the first event)
The beat engine's first beat fires at the South Gate: arrival prose describing the city, ending with
the guard's first line prompting `look`. Completion condition: the player inputs `look`.

### Beat 5 — Guard guidance
After `look`, the guard prompts movement north to the plaza and the guild. `talk` with the guard
serves scripted keyword responses (公會 / 冒險 / 危險 / 再見). Guidance ends when the player reaches
the guild exterior.

### Beat 6 — First-day arc (existing systems)
Guild registration (F rank) → accept 討伐低階魔物 from the board → North Gate → wilderness →
`engage` a low-tier monster (overwhelm-compressed combat) → return and turn in.

### Beat 7 — First day complete
Turn-in success sets `onboarded = True` and shows a closing line. No further guidance afterwards.

### Skip
At any beat the player may walk away; the guard does not block. Skipping records "guide skipped"
without setting `onboarded`, so `help` (a 新手引導 entry) and `talk` with the guard remain available.

---

## 4. Architecture

### 4.1 Layers (single writer preserved)

```
┌─ Presentation ────────────────────────────────────────────┐
│  Connection screen      CONNECTION_SCREEN_MODULE custom    │
│  Welcome / introduction  prose shown after login           │
│  Character creation      restyled `character` command      │
│  CmdsTalk               `talk` command in CharacterCmdSet  │
└────────────────────────────────────────────────────────────┘
┌─ Guidance layer (read-only)  world/onboarding/ ───────────┐
│  scenes.py            arrival-beat data (prose + trigger + │
│                       continuation)                        │
│  guide_dialogue.py    guard keyword → response table       │
│  guide.py             beat coordinator: reads state,       │
│                       returns the next prose/prompt (pure) │
└────────────────────────────────────────────────────────────┘
┌─ Deterministic core (sole writer)  world/rules/ ──────────┐
│  onboarding.py         state service:                      │
│    activate_teleport()   activation → South Gate           │
│    advance_beat()        beat progression                  │
│    mark_guide_skipped() / set_onboarded()                  │
│    talk_response()       guide dialogue progress           │
│    sync_guard_npc()      idempotent startup NPC creation   │
│  South Gate guard NPC                                      │
└────────────────────────────────────────────────────────────┘
```

### 4.2 Component responsibilities

| Component | Responsibility | Depends on |
|---|---|---|
| `world/onboarding/scenes.py` | immutable arrival-beat data | none (registry style, like `quests/definitions.py`) |
| `world/onboarding/guide_dialogue.py` | immutable keyword→response table | none |
| `world/onboarding/guide.py` | decide the next beat; output prose/prompts | onboarding data, rules state reads |
| `world/rules/onboarding.py` | all state writes; guard sync; public API | existing rules APIs (movement, traits) |
| `commands` (`CmdsTalk`, `character` restyle) | player input → rules/guide APIs | the above |

### 4.3 Key decisions

1. **The guard is not a new typeclass.** It is an ordinary `NPC(LivingEntity)` carrying an
   `OnboardingGuide` component (following the `GuildStaff` / `Merchant` component pattern), holding
   its guide progress. It is created idempotently at startup by `sync_guard_npc()`, mirroring the
   existing guild-economy NPC sync.
2. **`CmdsTalk` works on any NPC** but responds only when the NPC carries a dialogue component;
   otherwise the player gets "對方沒有理會你". This is layered cleanly away from change 19's LLM
   dialogue, which uses the existing `NPC.dialogue_memory` seam.
3. **Beat progress lives in character attributes**; reconnection resumes from the current beat.
4. **Teleport uses the existing movement path** (`world/rules/movement.py`), not a new move
   mechanism.

---

## 5. State, Persistence, Reconnect, Skip

### 5.1 Persisted state (all `AttributeProperty` on the player character)

| Field | Type | Writer | Meaning |
|---|---|---|---|
| `onboarded` | bool, default False | rules | first-day journey complete |
| `onboarding_beat` | int \| None | rules | current beat; None = not started |
| `guide_progress` | dict | rules | guide dialogue progress |
| `first_arrival_seen` | bool | rules | whether the arrival scene has played |

All writes go through `world/rules/onboarding.py`; nothing writes these attributes directly.

### 5.2 Reconnect behavior

- Not onboarded + arrival seen → resume in place, guide progress preserved.
- Not onboarded + arrival not seen → replay Beat 4 (arrival scene).

### 5.3 Skip

- Walking away marks "guide skipped"; `onboarded` is set only on first hunt turn-in.
- `help` gains a 新手引導 entry; `talk` with the guard still answers basic questions.

### 5.4 Edge cases

- Mid-journey disconnect → all state lives on character attributes; safe to resume.
- Activation then immediate quit → reconnect at the South Gate; arrival replays if unseen.
- `engage` on the guard → targeting rejects (the guard has no combat component); no special case.
- Repeated sync → no duplicate NPC (idempotent by stable key/tag).

---

## 6. Error Handling and Degradation

| Situation | Behavior |
|---|---|
| LLM / image services offline | no-op; the journey is fully deterministic |
| Beat data missing or unreadable | fall back to unguided arrival; play continues |
| `sync_guard_npc()` fails (e.g. South Gate missing) | `log_warn`; skip guidance; the player still teleports |
| Teleport fails after activation | teleport is independent of activation (activation must not depend on world state); the player stays put with an explanation, and activation remains valid |

---

## 7. Testing Strategy

| Area | Method |
|---|---|
| Beat engine | one test per beat, mirroring the rulebook "one test per rule ID" convention |
| Guide dialogue table | one test per keyword group |
| Full journey | `EvenniaTest` covering login → create → activate → teleport → `look` → `north` → register → hunt → turn in → `onboarded=True` |
| Reconnect / skip / disconnect | one test per scenario |
| Spec amendment | `player-character-creation`'s "activation does not move" scenarios updated together with the delta |
| Traceability | new main-spec requirements annotated with `covers_requirement`; `spec_traceability check` passes |

---

## 8. OpenSpec Integration

Two changes, matching the project's one-change-per-day cadence:

1. **`login-creation-ux`** — connection screen, world introduction, `character` command restyle.
2. **`onboarding-guide`** — beat engine, `OnboardingGuide` component, guard dialogue, arrival
   scene, state service, teleport, and the spec amendment.

`player-character-creation` requires a `MODIFIED` delta rewriting the clause
"Activation SHALL not create, move, or puppet an object; the shell's dbref, account relation,
location, and puppeting remain unchanged" to allow teleport to the starting location, with its
scenarios updated accordingly.

---

## 9. Out of Scope

- Generative NPC dialogue (change 19). The guard's scripted table is deterministic and separate.
- Scene art (change 22). No image is required; the design leaves the `scene_archetype` seam
  untouched and does not block on art.
- Multi-character accounts and alternate starting characters.
- Any change to combat, quest, guild, shop, or clock mechanics beyond the arrival hook.
