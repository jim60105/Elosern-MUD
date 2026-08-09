# PersonaStore and Dialogue Persona Injection — Design

**Date:** 2026-08-09
**Status:** Approved
**Scope:** The `PersonaStore` handler seam (master design §5.2), NPC- and player-persona
injection into the LLM dialogue prompt, and the output-side no-leak extension.

This document is a slice of the master design
(`docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`, §5.2 `PersonaStore`). Where this
document conflicts with the master design, the master design wins unless this document explicitly
amends it.

---

## 1. Product Context

The master design §5.2 describes `PersonaStore` as doing three things and nothing else: persist
imported fields verbatim, retrieve by key, flatten into prompt blocks. As of 2026-08-09 only the
persist half exists: validated imports store `persona` verbatim on `entity.db.persona` via
`world/imports/loader.py`, while the `PersonaStore` class, keyed retrieval, and prompt-block
flattening are unimplemented and unclaimed. The `living-entity-hierarchy` main spec keeps
`persona` a declared seam (its scenario asserts no `PersonaStore` class definition exists), and the
`affinity-system` change explicitly kept persona the only `None` placeholder seam.

Nothing in the game reads persona today. This change claims the seam and makes persona real prompt
material for the one consumer the master design points at: NPC-dialogue persona injection.

The dialogue pipeline is live and guarded: `typeclasses/npcs.py::LLMNPC.at_talked_to` builds the
prompt through `world/ai/npc_dialogue.py::build_npc_dialogue_prompt` (a deterministic pure function
with bounded serialization), runs the guarded reply pipeline, and applies verified intents through
`world/rules/npc_intents.py`. The affinity system already injects a per-call secret context
(`player.affinity`) and guards it with a per-call semantic no-leak validator
(`world/ai/npc_dialogue.py::_make_no_affinity_leak_validator`). Persona injection extends this
existing plumbing; it does not add a new transport, schema, or degradation path.

**Deterministic and offline constraint.** Persona injection is prompt material only. With the LLM
entirely offline the dialogue layer degrades exactly as it does today (authored greeting or
silence); persona presence or absence never changes that behavior.

---

## 2. Design Decisions

| # | Decision | Rationale |
|---|---|---|
| P1 | **Bidirectional injection.** The NPC's own persona feeds its system prompt (in-character); the player character's persona feeds the user payload (the NPC recognizes its conversation partner). | Mirrors the existing injection layering (identity + `disguised_stats` for the player; role for the NPC). One call carries both materials. |
| P2 | **Flatten exactly three fields: `personality`, `life_story`, `habit`.** | `identity` overlaps the existing `{name}` role material; `appearance` is already covered by localized-appearance and the art portrait pipeline; `social_connection` is unbounded and not conversation-personality material. |
| P3 | **Flattening performs no content filtering** (authored content is preserved verbatim), and leak protection is **output-side only**. | Persona is author-authored card content, not engine-computed secret state. The engine's secret contract is about what a reply may reveal, so the guard lives at the reply validator. |
| P4 | **Generalize the no-leak validator to a bounded secret set: affinity value/cap (existing) plus true trait values under an active disguise** (`atk_phys`, `agility`, `defense`, `magic_level`, `hp` when `disguised_stats` exists and differs from the true values). | Completes the D2 display-layer secrecy contract: the NPC perceives `disguised_stats` and must never speak true values. The set is bounded and per-call. |
| P5 | **`PersonaStore` is a read-only handler in `world/rules/persona.py`, mounted on `LivingEntity.persona`** (replacing the placeholder `AttributeProperty`), reading raw data from `entity.db.persona`. | Follows the `RelationHandler` mount pattern (`world/rules/affinity.py`); the handler carries no write API, preserving the single-writer boundary — `world/ai/` still never writes, and import-loader's verbatim storage path is untouched. |
| P6 | **Prompt material flows through the prompt library**: `npc_dialogue.system` gains a `{persona}` placeholder and the user payload gains a `player.persona` block. | Keeps prompt text data-driven and swappable per the externalized-prompt-library contract; registry placeholder allowlists enforce bounds. |

---

## 3. System Design

### 3.1 PersonaStore

`world/rules/persona.py`:

```python
class PersonaStore:
    """Read-only handler over an entity's verbatim persona record."""

    def __init__(self, entity): ...
    def flatten(self, fields=("personality", "life_story", "habit")) -> str | None
```

Behavior:

- Reads `entity.db.persona`; a non-dict value, a missing record, or a record with none of the
  configured fields present yields `None` (no block) — never an exception.
- `flatten()` emits one labeled section per present field in the declared field order
  (e.g. `性格：…` / `人生經歷：…` / `習慣：…`), each field string capped with the project's
  `_cap_string` idiom and the combined block capped at a total bound.
- No write API, no import of any state-mutating module, no trait or attribute access beyond the
  single persona record.

Mount: `typeclasses/entities.py` replaces `persona: Any | None = AttributeProperty(default=None)`
with a `lazy_property` returning `PersonaStore(self)`, mirroring the `relations` mount. Raw storage
stays at `entity.db.persona`; `world/imports/loader.py` is unchanged.

### 3.2 Dialogue injection

`world/ai/npc_dialogue.py` (all additions keep the module's no-typeclass, no-writer discipline):

- `_system_message(npc_context)` renders `npc_dialogue.system` with an additional optional
  `persona` value (capped). `world/prompts/registry.py` extends the `npc_dialogue.system` spec's
  allowed placeholders with `persona`.
- `build_npc_dialogue_prompt(...)` accepts an optional `npc_persona: str | None` and
  `player_persona: str | None`; the user payload gains `player.persona` beside `player.affinity`
  when present. Identical input still produces byte-identical prompts.

`typeclasses/npcs.py::LLMNPC.at_talked_to` (read-only):

- builds the NPC's persona block via `self.persona.flatten()` and the speaking player's via
  `character.persona.flatten()`;
- computes the no-leak secret set: affinity value/cap (existing) plus true trait values when the
  NPC has an active disguise whose `disguised_stats` differ from the true values;
- passes both through the existing `run_npc_exchange` / `at_talked_to` context, exactly like the
  affinity context is passed today. `world/ai/` never imports a typeclass.

### 3.3 No-leak extension

`_make_no_affinity_leak_validator(value, cap)` generalizes to a factory over a bounded secret set:

```python
def _make_no_leak_validator(secrets: frozenset[str]) -> Callable[[Any], list[str]]
```

- Affinity calls keep their current two-secret binding (value, cap) through the same factory, so
  existing behavior and tests are preserved.
- Disguise secrets are bound only when a disguise is actually active and differs from the true
  values; otherwise the set stays affinity-only.
- A reply whose speech echoes any bound secret goes through the existing reject/retry/degrade
  flow; retry exhaustion degrades to the authored fallback and never presents the number.

---

## 4. Integration Points

| Integration | Direction |
|---|---|
| `world/imports/loader.py` | Unchanged: verbatim `entity.db.persona` storage is the only writer |
| `typeclasses/entities.py` | `persona` placeholder attribute flips to the `PersonaStore` mount (flips `living-entity-hierarchy`'s no-PersonaStore scenario) |
| `typeclasses/npcs.py` | `at_talked_to` supplies persona blocks and the extended secret set (read-only) |
| `world/ai/npc_dialogue.py` | Prompt build, bounded serialization, generalized no-leak validator |
| `world/prompts/registry.py` + `prompts/npc_dialogue.yaml` | `{persona}` placeholder allowlist + template text |
| Guardrail | No new layer; existing semantic-validator registration mechanism carries the generalized validator |

---

## 5. Error Handling and Degradation

| Situation | Behavior |
|---|---|
| persona missing / malformed / all fields absent | Persona block omitted; prompt byte-identical to today's output |
| Field or block over length bound | Capped, never rejected |
| LLM offline / retry-exhausted | Existing greeting/silence degrade; no new path |
| Reply echoes a bound secret | Existing reject/retry; exhaustion degrades, number never shown |
| No active disguise | Secret set = affinity only; no new bindings |

---

## 6. Testing Strategy

| Area | Method |
|---|---|
| PersonaStore | Pure `unittest.TestCase`: three-field flattening order and labels, field/block caps, malformed record, missing fields, `None`; no write API surface |
| Injection | `FakeLLMClient` replays: NPC persona present/absent, player persona present/absent, byte-identical stable prompts, bounded serialization, offline degrade |
| No-leak | Existing affinity-validator tests stay green; new tests: echo of a true trait value under disguise rejects/retries; per-call binding isolation; no binding without active disguise; exhaustion degrades without presenting the number |
| Traceability | New main requirements annotated with `covers_requirement`; `spec_traceability check` passes |

---

## 7. OpenSpec Slicing

Two sequential per-day changes, each landing and verifying independently:

| # | Change | Depends on | Content |
|---|---|---|---|
| 1 | `persona-store` | 3 (`entity-traits`), 4 (`import-contract`), 8/17 (dialogue pipeline) | `PersonaStore` handler, mount flip on `LivingEntity.persona`, flatten bounds, unit tests; `living-entity-hierarchy` delta flips the no-PersonaStore scenario |
| 2 | `persona-dialogue-injection` | 1, 17 (`llm-client`), 19 (`npc-dialogue`), 23d dialogue surface | `{persona}` placeholder + registry allowlist, `player.persona` payload block, `at_talked_to` context plumbing, generalized no-leak validator, FakeLLMClient tests |

---

## 8. Out of Scope

- Generative character creation using persona (a future `character_creation.system` change owns that).
- Content filtering or schema validation of persona content at import or flatten time (P3).
- Injection of persona into Narrator, ScenarioDirector, or scene prompts.
- Any player-facing display of persona content.
- Decrease events, cap breaks, or any affinity change (owned by the affinity-cap-break design).

---

## 9. Open Questions Carried Forward

- None blocking. A future change that needs persona beyond the three flattened fields (for example
  importing `appearance` or `social_connection` into art or scene prompts) extends the flatten
  field tuple and bounds, which this design keeps configurable at the call site.
