## ADDED Requirements

### Requirement: Generation resolves to an OptionSet or the None degrade outcome

`world/ai/action_options.py` SHALL provide a guarded entry point
`generate_action_options(context, client, *, fingerprint) -> defer.Deferred` that runs the
`action_options` layer's validation-retry-degrade pipeline and resolves, on success, to a frozen
`OptionSet` (always `status: "ready"`) carrying between `MIN_CARDS` (3) and `MAX_CARDS` (5)
cards; on a disabled profile, a transport failure, or exhausted retries it SHALL resolve to
`None` — the deterministic rules take over (`suggestions=degraded`), with no partial success and
no state change. The client SHALL be a required injected argument; the call SHALL invoke
`client.get_response` with a descriptor carrying `schema_id="action_options"` and the registered
output schema, and SHALL request structured output only per the profile's
`supports_response_format` capability. The profile gate SHALL run before any prompt construction
or transport work. The `fingerprint` SHALL be required and opaque to the layer: it is carried
from the caller into the enriched `OptionSet` and into the ladder entry point, and is never
rendered into the prompt.

#### Scenario: A valid proposal resolves with no retry
- **WHEN** the endpoint returns a card set satisfying the registered output schema, the
  enrichment, the ladder, and the 3–5 generation floor on the first attempt
- **THEN** `generate_action_options` resolves with a frozen `OptionSet` carrying all cards in
  prompt order and performs no retry

#### Scenario: A disabled profile resolves to None without transport
- **WHEN** the `action_options` profile is disabled
- **THEN** the call resolves to `None` immediately and the client's `get_response` is never
  invoked

#### Scenario: A transport failure resolves to None without retries
- **WHEN** the endpoint times out, fails, or returns a malformed body
- **THEN** the call resolves to `None` immediately with no retry loop on the same broken
  transport, and the deterministic game continues unaffected

### Requirement: Bounded-context serialization is public-only and truncation-ordered

The context builder SHALL assemble a frozen context from caller-supplied plain data with hard
budgets: `room_name` ≤ 40 chars, `room_summary` ≤ 300, `narrative_tail` ≤ 600, `npc_entries` ≤ 8
with persona digests ≤ 160 chars each, `monster_entries` ≤ 4 with ≤ 80 chars each, `objective`
≤ 120, and `affordances` ≤ 16 entries. Truncation SHALL follow the fixed order: narrative tail is
dropped first, then persona-digest characters, then NPC entries (oldest first);
`affordances`, `room_name`, and `room_summary` SHALL never be truncated. The context builder SHALL
emit a `LEAK_BLOCKLIST` (numeric literals and hidden trait keys of the deterministic view) that is
consumed by validation only and never serialized into the prompt. NPC entries SHALL carry stable
positional identity so the prompt's `{npc_index}` references resolve deterministically.

#### Scenario: Over-budget context truncates in the fixed order
- **WHEN** the call-site passes a context whose tail exceeds 600 chars, a digest exceeds 160, and
  more than 8 NPCs are present
- **THEN** the tail is dropped first, then digest characters, then the oldest NPC entries, while
  the affordance list, room name, and room summary remain complete

#### Scenario: An over-budget non-truncatable value is a named input error
- **WHEN** the call-site passes an affordance list exceeding 16 entries, or a room name or summary
  exceeding its cap
- **THEN** the builder raises a named `ActionOptionsInputError`, the entry point catches it and
  resolves `None`, and no out-of-bounds data is ever emitted or rendered

#### Scenario: A leak blocklist is composed but never prompts
- **WHEN** the deterministic view contains true-trait numbers and hidden trait keys
- **THEN** the context carries those tokens in the blocklist only, the rendered prompt contains
  none of them, and no raw affinity or true-trait number is serialized

#### Scenario: Identical input produces byte-identical context
- **WHEN** the same plain-data inputs are passed twice
- **THEN** the builder returns an identical frozen context with no live entity references

### Requirement: Prompt assembly honors the registered placeholder allowlist

`build_action_options_prompt(context)` SHALL render the system/user message pair through the
prompt library's two `action_options` keys (`render_prompt("action_options.system", ...)` and
`render_prompt("action_options.user", ...)`) using exactly the seven `ActionOptionsContext`
fields as the user message's substitution keys and no context tokens in the system message,
substituting only placeholders allowlisted per key in `world/prompts/registry.py`. The
affordance list in the user message SHALL carry each entry's canonical `action_id` + typed
params and the NPC entries SHALL carry their stable `{npc_index}` references so freeform cards
can target a present person without the model typing an id. A placeholder parity contract test
SHALL assert each key's allowlist equals the serialized fields it renders (asserting the user
key's allowlist equals the real field set and the system key's is empty), and the module SHALL
NOT embed prompt text as a Python constant.

#### Scenario: The rendered user message exposes the vocabulary and bindings
- **WHEN** a context with two NPCs and three affordances is rendered
- **THEN** the user message contains the affordance list with canonical payloads and the two NPC
  entries with their positional indices, and contains no placeholder tokens outside the allowlist

#### Scenario: An unregistered placeholder fails loudly
- **WHEN** the prompt file declares a placeholder that is absent from the allowlist
- **THEN** the prompt-library contract test fails with a named error, and no render proceeds with
  an unverified placeholder

### Requirement: Freeform NPC references are bound before validation

Raw freeform cards SHALL carry `{npc_index}` against the prompt's bound NPC list; before ladder
validation the layer SHALL resolve each reference into
`{"action_code": "explore.talk_freeform", "params": {"npc_id": int}}` and SHALL inject the
caller-supplied `fingerprint` and `status: "ready"` into the raw output (these two fields are
never produced by the model). An unknown index or a target bound twice SHALL reject the
offending card and enter the retry loop.

#### Scenario: Single and multiple NPC references resolve
- **WHEN** the endpoint emits freeform cards referencing `npc_index` 0 and 1 against a two-NPC
  context
- **THEN** the resolved cards carry `action_code "explore.talk_freeform"` and the bound `npc_id`
  values of the prompt's NPC entries in positional order

#### Scenario: An unknown index is rejected and retried
- **WHEN** a freeform card references an `npc_index` outside the bound NPC list
- **THEN** the card is rejected with a binding error, the error is appended to the prompt for the
  retry, and exhaustion of the budget resolves to `None`

### Requirement: Validation failures retry within the bounded budget

The generated output SHALL be validated by the layer's per-call semantic validator — a total
function running enrichment, the freeform binding, and then the full ladder via the schema
change's entry point `validate_optionset(raw, *, fingerprint, affordances, leak_blocklist)`
(canonical affordance match against the context's affordance tuple replacing model-typed params,
leak gates on labels/hints, count bounds, and the text gates the ladder owns) — and the result
SHALL carry the caller-supplied `fingerprint` and the context's `LEAK_BLOCKLIST` through the
ladder. A set the ladder accepts with fewer than `MIN_CARDS` (3) cards SHALL be rejected as a
generation-rule failure by the layer. Any rejection SHALL append the round's complete error
message to the prompt and retry within the `1 + max_retries` budget; exhaustion SHALL resolve to
`None`. A transport failure SHALL NOT enter this loop. The validator SHALL NEVER raise into the
pipeline: parsing, enrichment, binding, or ladder exceptions SHALL be converted into named error
messages (ladder rejections as `"stage N: <code>"`) and returned with the round's error list.

#### Scenario: Invalid output is retried with the errors appended
- **WHEN** the endpoint returns output that fails the ladder or the enrichment/binding step
- **THEN** the pipeline retries up to the `1 + max_retries` budget with that round's full
  validation error list appended, and never returns invalid output

#### Scenario: A set below the generation floor never escapes the loop
- **WHEN** the endpoint returns 0, 1, or 2 cards that nonetheless pass the ladder
- **THEN** the layer rejects the set as a generation-rule failure, the rejection retries within
  the budget, and exhaustion resolves to `None` — an OptionSet with fewer than 3 cards is never
  resolved

#### Scenario: A ladder exception becomes a named message, not a crash
- **WHEN** the ladder entry point raises a named per-stage error during a round
- **THEN** the round's error list contains `"stage N: <code>"`, the retry proceeds within the
  budget, and no exception escapes the validator or the pipeline

#### Scenario: Exhausted retries degrade to None
- **WHEN** every attempt returns output that still fails validation
- **THEN** the call resolves to `None` and the deterministic game continues unaffected

### Requirement: Guardrail hooks install atomically and idempotently

`register_action_options()` SHALL install the layer's degrade fallback and the `action_options`
output schema (validating the model's raw wire shape: optional `params` on `known_action` cards
and `npc_index` on `freeform` cards — never the caller-injected `fingerprint`/`status`/
`action_code`/`params`) through the guardrail registry seam, atomically and idempotently: a
second call SHALL be a no-op that keeps the first registration, and a partial registration
failure SHALL remove every hook the module itself installed before the error propagates (never
a half-registered layer). Server startup SHALL register the layer beside the other generative
layers; when the `action_options` profile slot or the schema registry is not yet available, the
startup wrapper SHALL log a bounded warning and skip registration instead of aborting startup.

#### Scenario: Double registration is a no-op
- **WHEN** `register_action_options()` is called twice
- **THEN** the guardrail holds exactly one fallback and one output schema for the layer, and the
  second call changes nothing

#### Scenario: A partial failure rolls back its own hooks
- **WHEN** a hook installation fails mid-registration
- **THEN** every hook belonging to this module is removed, and the layer is not left
  half-registered

#### Scenario: Missing prerequisites skip registration, never abort startup
- **WHEN** the `action_options` profile slot (prompts change) or the schema entry point (schema
  change) is absent at server startup
- **THEN** startup logs a bounded warning, skips the layer's registration, and completes
  normally; a later explicit call of `register_action_options()` after the prerequisites land
  installs cleanly

### Requirement: The layer is strictly proposal-only

`world/ai/action_options.py` SHALL import no state writer, no live transport, and no socket at
module import time (the existing transport-contract test SHALL cover it); the client SHALL be the
injected protocol. The module SHALL never persist, spawn, or mutate canonical game state — its
only outputs are the frozen `OptionSet` proposal and `None` — and SHALL log through `evennia`
logger without binding a module-level logger object.

#### Scenario: The transport boundary holds
- **WHEN** the transport-contract test inspects the module's imports
- **THEN** no state writer, live transport, or socket appears at module import time, and the
  client is only ever the injected argument

#### Scenario: A proposal never mutates state
- **WHEN** a generated `OptionSet` is handed across the `world/ai` boundary
- **THEN** the module performed no persistent write, spawn, or trait/attribute mutation, and the
  returned object is frozen with no mutable containers