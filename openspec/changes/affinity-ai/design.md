# affinity-ai Design

## Context

`affinity-system` delivered the sole-writer affinity API (`apply_affinity_change` with the closed
source set and the capped `ai_dialogue` source) and the stage ladder. The `npc-dialogue` layer has
whitelisted `adjust_relation` since change 19 but the deterministic applier forward-declares it.
This change connects the two: the AI decides a bounded affinity delta (0–10) per exchange and the
NPC sees its true affinity toward the player in the prompt. Constraints: the single-writer
invariant (`world/ai/` never writes; the applier lives in `world/rules/`), the transport boundary
test (`tests/test_ai_transport_contract.py` must stay green unedited), deterministic byte-identical
prompts, and offline degradation unchanged.

## Goals / Non-Goals

**Goals**

- Enforce the 0–10 `delta` bound in the schema and in a per-kind semantic validator.
- Route `adjust_relation` through `apply_affinity_change(..., "ai_dialogue", delta)` with the
  budget-capped and invalid-payload outcomes keeping the speech.
- Inject the NPC's affinity context (value, cap, stage) into the dialogue user payload, read-only.
- Teach the `npc_dialogue.system` prompt template to use the affinity context (library data).
- Cover the new validator, applier, prompt block, and seam with `FakeLLMClient`-driven tests.

**Non-Goals**

- `party_invite` (change `party-core`), decrease events, cap breaks, any numeric player display.

## Decisions

### D-1: The delta bound lives in the schema and a semantic validator, exact shape in the validator

The output jsonschema `intent.properties.delta` gets `{"type": "integer", "minimum": 0,
"maximum": 10}`; the schema bounds the value when present (the schema does not carry
`additionalProperties: false`, so it cannot express per-kind exact shape on its own). The
**exact** single-field shape (`{"delta": ...}` only, no extra fields, bool excluded) is enforced
by a per-kind semantic validator, following the exam/item payload precedent; the deterministic
applier rechecks the same shape before writing. A malformed delta is retried within the budget
and never reaches the engine.

### D-2: The applier reports the applied amount; partial application is success

`apply_npc_intent` verifies shape (exactly `delta`, int, 0–10), then calls
`world/rules/affinity.py::apply_affinity_change(npc, player, "ai_dialogue", delta)`. The writer
owns budget, cap, and partial-delta semantics (specified in `affinity-system`: requested 4 with
budget 2 applies 2). The applier maps the writer outcome by the **actual applied amount**, not by
the capped flag: `delta_used > 0` → `IntentOutcome(applied=True, delta_used=…)` even when the
budget was also capped; `delta_used == 0` (fully budget-capped or rejected) → applied=False, no
state change, speech preserved. `IntentOutcome` gains a `delta_used` field filled only by the
relation path.

### D-3: Affinity context is a fixed, capped, read-only user-payload block

`build_npc_dialogue_prompt` accepts `affinity_context: dict | None` and serializes it as
`player.affinity = {"value": int, "cap": int, "stage": str}` through the existing `_cap_value`
bounds. `LLMNPC.at_talked_to` reads the NPC's own record for the speaking player through the
read-only relations handler — `has_record(player)` gating, then the value/cap accessor and
`stage_for(player)`; it never calls the writer and a recordless player yields `None` (block
omitted). Prompts remain byte-identical for identical inputs.

### D-4: The system-prompt guidance is library data, not code

The `npc_dialogue.system` template in `prompts/npc_dialogue.yaml` gains a sentence on choosing
`adjust_relation` deltas from the supplied affinity values within 0–10, and a rule that the
numeric affinity value and cap are secrets the NPC must never speak aloud. Module code only
passes data; prompt text is tuned by editing the library (single-source-of-truth contract,
`prompt-library`). The allowlisted placeholder set (`{name}`, `{desc}`, `{location}`) is
unchanged.

### D-5: Numeric affinity values are kept out of player-facing speech deterministically

Prompt instructions alone cannot guarantee secrecy, so the layer adds the semantic validator
`no_affinity_leak`: when an affinity context is present, a reply whose speech contains the
affinity value or the cap as a decimal integer substring is treated as a validation failure,
appended to the retry errors, and retried within the budget; on budget exhaustion the call
degrades to `None` (greeting or silence), never presenting a leak. Stage names remain allowed in
speech — they are the sanctioned player-facing form. The validator runs only when the affinity
block was injected, so ordinary dialogue is unaffected.

## Risks / Trade-offs

- [The model returns a delta the budget rejects; the player sees no gain] → partial deltas apply
  and are reported as applied; a fully blocked delta is discarded, the speech kept; no numeric cap
  is exposed.
- [The model echoes the secret affinity value or cap in speech] → the `no_affinity_leak`
  validator rejects such replies and retries; exhausted retries degrade to greeting/silence, never
  presenting a leak (D-5).
- [Prompt grows with the affinity block] → the block is three bounded fields through `_cap_value`;
  total size stays under the existing `MAX_TOTAL_SIZE` budget.
- [Seam accidentally writes while injecting] → the seam calls only read APIs; a test asserts the
  stored record is byte-identical after a talk; a corrupted-record regression test proves the seam
  still degrades instead of crashing.
- [Validator drift between schema and per-kind checks] → one validator function per payload shape,
  matching the exam/item precedent, each with a rejected-payload test; the schema bounds the value
  when present and the exact-shape responsibility is explicitly assigned to the validator and the
  applier recheck.

## Migration Plan

No released users; no data migration. The applier's forward-declared rejection for
`adjust_relation` is replaced by the real delegation; `offer_quest` / `reveal_lore` remain
forward-declared. Rollback is a revert; a stored record with an out-of-range shape is treated as
malformed and discarded by the validator.

## Open Questions

- None blocking. Whether the affinity block is nested under `player` or a top-level key is a
  prompt-serialization detail fixed in implementation, keeping byte-identical determinism either
  way.
