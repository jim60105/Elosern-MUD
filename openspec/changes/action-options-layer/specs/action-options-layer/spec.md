## ADDED Requirements

### Requirement: Generation resolves to an OptionSet or the None degrade outcome

`world/ai/action_options.py` SHALL provide a guarded entry point
`generate_action_options(context, client) -> defer.Deferred` that runs the `action_options`
layer's validation-retry-degrade pipeline and resolves, on success, to a frozen `OptionSet`
(always `status: "ready"`); on a disabled profile, a transport failure, or exhausted retries it
SHALL resolve to `None` — the deterministic rules take over (`suggestions=degraded`), with no
partial success and no state change. The client SHALL be a required injected argument; the call
SHALL invoke `client.get_response` with a descriptor carrying `schema_id="action_options"` and the
registered output schema, and SHALL request structured output only per the profile's
`supports_response_format` capability. The profile gate SHALL run before any prompt construction
or transport work.

#### Scenario: A valid proposal resolves with no retry
- **WHEN** the endpoint returns a card set satisfying the registered output schema and every
  semantic validator on the first attempt
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

#### Scenario: A leak blocklist is composed but never prompts
- **WHEN** the deterministic view contains true-trait numbers and hidden trait keys
- **THEN** the context carries those tokens in the blocklist only, the rendered prompt contains
  none of them, and no raw affinity or true-trait number is serialized

#### Scenario: Identical input produces byte-identical context
- **WHEN** the same plain-data inputs are passed twice
- **THEN** the builder returns an identical frozen context with no live entity references

### Requirement: Prompt assembly honors the registered placeholder allowlist

`build_action_options_prompt(context)` SHALL render the system/user message pair through the
prompt library (`render_prompt("action_options.system", ...)`) using exactly the
`ActionOptionsContext` fields, substituting only allowlisted placeholders registered for the
`action_options` key in `world/prompts/registry.py`. The affordance list in the user message
SHALL carry each entry's canonical `action_id` + typed params and the NPC entries SHALL carry
their stable `{npc_index}` references so freeform cards can target a present person without the
model typing an id. A placeholder parity contract test SHALL assert the allowlist equals the
serialized context fields, and the module SHALL NOT embed prompt text as a Python constant.

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

The generated output SHALL be validated against the `action_options` registered output schema,
the layer's registered semantic validators, and the full ladder (canonical affordance match
against the context's affordance tuple replacing model-typed params, leak gates on labels/hints,
CJK/length/placeholder/digit gates) via the schema change's entry point. Any rejection SHALL
append the round's complete error message to the prompt and retry within the `1 + max_retries`
budget; exhaustion SHALL resolve to `None`. A transport failure SHALL NOT enter this loop.

#### Scenario: Invalid output is retried with the errors appended
- **WHEN** the endpoint returns output that fails the ladder or a semantic validator
- **THEN** the pipeline retries up to the `1 + max_retries` budget with that round's full
  validation error list appended, and never returns invalid output

#### Scenario: Exhausted retries degrade to None
- **WHEN** every attempt returns output that still fails validation
- **THEN** the call resolves to `None` and the deterministic game continues unaffected

### Requirement: Guardrail hooks install atomically and idempotently

`register_action_options()` SHALL install the layer's degrade fallback, every semantic
validator, and the output schema through the guardrail registry seam, atomically and
idempotently: a second call SHALL be a no-op that keeps the first registration, and a partial
registration failure SHALL remove every hook the module itself installed before the error
propagates (never a half-registered layer). Server startup SHALL register the layer beside the
other generative layers.

#### Scenario: Double registration is a no-op
- **WHEN** `register_action_options()` is called twice
- **THEN** the guardrail holds exactly one fallback, one set of validators, and one output schema
  for the layer, and the second call changes nothing

#### Scenario: A partial failure rolls back its own hooks
- **WHEN** a hook installation fails mid-registration
- **THEN** every hook belonging to this module is removed, and the layer is not left
  half-registered

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