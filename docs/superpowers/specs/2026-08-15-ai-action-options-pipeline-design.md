# AI Action Options — Generative Pipeline

**Date:** 2026-08-15
**Status:** Approved
**Scope:** `world/ai/action_options.py` — the bounded-context serializer, prompt construction, LLM
invocation under the `action_options` profile, retry policy, and the validation/degrade ladder that
produces an `OptionSet | None` (`None` = degrade to deterministic rules).

Part of the [AI Action Options document set](2026-08-15-ai-action-options-overview-design.md).
This module proposes only; every state-adjacent step (session lookup, coordinator push, cache
write) lives in the trigger service ([trigger-service](2026-08-15-ai-action-options-trigger-service-design.md)),
and the closed action vocabulary comes from the deterministic affordance builders
([deterministic-actions](2026-08-15-ai-action-options-deterministic-actions-design.md)).

---

## 1. Module Shape

`world/ai/action_options.py` contains pure functions and frozen structs only:

```
ActionOptionsContext {        # frozen; assembled by the trigger service from deterministic views
  room_name: str
  room_summary: str           # deterministic desc / scene sentence excerpt
  npc_entries: tuple[NPCEntry, ...]   # identity, display name, dialogue_key, persona digest, public tier
  monster_entries: tuple[MonsterEntry, ...]  # identity, display name, threat tier label
  objective: str | None       # public quest objective line, if any
  narrative_tail: str         # bounded recent narrative tail
  affordances: tuple[Affordance, ...]  # deterministic valid actions (vocabulary lock)
  leak_blocklist: frozenset[str]       # consumed by validation only, never by the prompt
}
```

Import discipline mirrors `server/scene_flavor_service.py`/`world/ai/narrator.py`: no Evennia
imports at module import time, no module-level logger binding, and the guardrail's degrade path
resolves before any transport work.

---

## 2. Bounded-Context Serialization

The context builder (`build_options_context(...)`) is called by the trigger service on the
deterministic side. Truncation policy is fixed order: narrative tail is dropped first, then persona
digest characters, then NPC count (oldest entries); `affordances`, `room_name`, and `room_summary`
are never truncated (a summary of what you *can't* do is useless).

| Field | Source (read-only accessors only) | Budget |
|---|---|---|
| `room_name` | room display name | ≤ 40 chars |
| `room_summary` | `room.db.desc` / scene sentence excerpt | ≤ 300 chars |
| `npc_entries` | present NPCs via the deterministic presence view; persona digest from `PersonaStore` public read | ≤ 8 entries, digest ≤ 160 chars each |
| `monster_entries` | present monsters | ≤ 4 entries, ≤ 80 chars each |
| `objective` | quest progress public view | ≤ 120 chars |
| `narrative_tail` | capped tail of the presentation event log | ≤ 600 chars |
| `affordances` | the canonical affordance list (deterministic-actions doc §1; never truncated) | ≤ 16 entries |
| `leak_blocklist` | numeric literals + hidden trait keys of the deterministic view | internal |

Public-tier relationship data uses the tier label (e.g. 好感層級), never the numeric affinity — the
same boundary `npc_dialogue` already observes. `affordances` carries each entry's canonical
payload (`action_id` + typed params + bound target) so the schema ladder's stage-9 exact match and
canonical replacement operate on the same data the prompt shows (schema doc §3.1).

---

## 3. Prompt Contract

New `prompts/action_options.yaml`, registered in `world/prompts/registry.py` with the placeholder
allowlist exactly matching the `ActionOptionsContext` fields:

- `system`: the assistant is a game-design curator for an adult single-player world; it proposes
  3–5 actions the protagonist *could* take next, in Traditional Chinese, always choosing from the
  provided affordance codes for `known_action` cards and only using `freeform` for speech the
  protagonist could plausibly say to a present person.
- `user`: the serialized context block, including the affordance list with each entry's canonical
  payload; NPC entries carry a stable `{npc_index}` so freeform cards reference a present person
  without the model typing an id.
- Hard rules repeated in the system prompt: no numbers, no hidden values, no fabricated targets,
  cards must reference only present people/places/things, exactly the JSON schema output.

The vocabulary lock (overview D-1) is enforced twice: the prompt shows only current affordances,
and the schema ladder stage 9 replaces model-typed params with the matching canonical payload and
rejects anything outside the list — a deterministic gate, not LLM discretion (schema doc §3).

---

## 4. Generation and Retry

`generate_action_options(context, client) -> defer.Deferred` resolves to `OptionSet | None`:

1. Profile gate: `action_options` profile disabled → resolve `None` (no transport work; the offline
   stub client never opens a socket).
2. Build prompt; call `client.get_response(descriptor)` with `schema_id="action_options"` and the
   inline JSON schema (schema doc §5).
3. Enrichment: inject the caller-supplied `fingerprint` and `status: "ready"`, and resolve freeform
   `{npc_index}` into `params: {"npc_id": int}` against the prompt's bound NPC list before
   validation (schema doc stage 0; unknown index or duplicate target → card rejection).
4. On success: `validate_optionset(...)` (schema doc §3). On any rejection, append the rejection
   message to the prompt and retry up to `max_retries` (profile); exhaustion → `None` (bounded log).
5. On `LLMTransportError` / timeout: resolve `None` immediately — retries for transport failures are
   the *service's* negative-memo job (trigger-service doc §3.5), not a hot-loop in the layer.

Degrade semantics are strict: `None` in, `suggestions=degraded` out. There is no partial success.

---

## 5. Profile

New slot `action_options` in `LAYER_NAMES` (`world/ai/profiles.py`) + `LLM_PROFILES["action_options"]`
in settings with `supports_response_format: true`; `world/ai/profiles.py`'s construction-time
validation rejects a false value at startup. Temperature defaults to the narrator profile's value
(0.7); `max_tokens` sized for a 5-card JSON payload (≈ 320).

---

## 6. Tests

| Area | Method |
|---|---|
| Context builder | Truncation order; blocklist composition; public-only data |
| Prompt | Placeholder allowlist parity (`world/prompts/registry.py` contract test); no hidden tokens in the serialized context |
| Success path | `FakeLLMClient` fixture → valid `OptionSet`; order preserved; fingerprint/status absent in output |
| Rejection ladder | One fixture per schema-doc rejection stage; retry consumes attempts; exhaustion → `None` |
| Transport | `add_timeout` / `add_http_error` / `add_connection_error` / `add_malformed_body` → `None`, no retry loop |
| Offline | Disabled profile → `None`; stub client `get_response` never called (assert in test) |

---

## 7. Open Questions Carried Forward

- Whether the persona digest should later admit affinity *tier* change cues ("她對你的態度變得
  親近") — the bounded context already carries the tier; a future change may enrich the narrative
  tail rule for dialogue contexts.