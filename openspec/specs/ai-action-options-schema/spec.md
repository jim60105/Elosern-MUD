## Purpose

The immutable suggestion-card vocabulary and validation ladder for the AI action-options
surface: the frozen `OptionSet`/`SuggestionCard` dataclasses, exact bounds constants, the
12-stage `validate_optionset` ladder with one named rejection code per stage, the stage-9
canonical replacement against the change-1 affordance vocabulary (vocabulary lock), the
freeform binding-only exception, the leak gates on label/hint, the enrichment helper, and the
exact-field `action_options` JSON contract parser. This capability owns the proposal-only
vocabulary; `action-options-layer` (generation), `action-options-trigger-service`
(cache/publish), and `context-actions-suggestions` (client mirror parity) consume it.

## Requirements

### Requirement: world/ai/action_options.py defines the frozen one-wire-shape card vocabulary
`world/ai/action_options.py` SHALL define frozen dataclasses `OptionSet` and `SuggestionCard`.
`SuggestionCard` SHALL carry exactly `kind` (`"known_action" | "freeform"`), `action_code` (a real
dispatcher action id string), `label` (player-facing text), `params` (`Mapping[str, str | int]`,
additionally admitting the exact boolean room-survey marker `{"room": true}` of the canonical
look payload, schema design doc §1.1), and optional `hint` — one wire shape, no hidden side
structure. `OptionSet` SHALL carry `fingerprint` (opaque string), `context_kind`
(`"exploration"` in v1), `status` (exactly `"ready"`), and a card tuple. Construction SHALL
reject mutable containers anywhere (`_reject_mutable_containers`, mirroring `QuestBlueprint` in
`world/ai/scenario_director.py`) so a proposal is safe to hand across the `world/ai` boundary.

#### Scenario: A proposal rejects mutable containers at construction
- **WHEN** an `OptionSet` is constructed with a list or dict nested inside its card params
- **THEN** construction raises and no proposal object is produced

#### Scenario: The cached status is always ready
- **WHEN** an `OptionSet` is constructed with `status` set to `"generating"` or `"degraded"`
- **THEN** construction rejects it — transport states are never cached (design doc §1.1)

### Requirement: The schema defines exact caps and a status-dependent card-count contract
`world/ai/action_options.py` SHALL define `MIN_CARDS`/`MAX_CARDS` (3/5), `MAX_LABEL_LENGTH` (24),
`MAX_HINT_LENGTH` (60), `MAX_PARAMS` (4 keys), the trigger-service bounds
`MAX_OPTIONSET_CACHE_ENTRIES` (16) and `NEGATIVE_MEMO_TTL` (30 seconds), and value shapes: ints
within `MAX_SAFE_INTEGER`, strings ≤ 32 chars, or the exact boolean room-survey marker
(`{"room": true}` of the canonical look payload, schema design doc §1.1). The validation ladder
SHALL accept 0–5 cards (stage 4); the 3–5 minimum is a *generation* rule owned by
`action-options-layer`, not a ladder rejection (three-layer contract, schema design doc §1.2).

#### Scenario: Card count within the acceptance band passes
- **WHEN** a proposal with 0 to 5 cards is validated
- **THEN** stage 4 accepts it without a `card_count_out_of_range` rejection

#### Scenario: A six-card proposal is rejected
- **WHEN** a proposal with 6 cards is validated
- **THEN** it fails stage 4 with the named rejection `card_count_out_of_range`

### Requirement: The validation ladder runs 12 fixed stages with one named rejection code each
`validate_optionset(raw, *, fingerprint, affordances, leak_blocklist=frozenset())` SHALL run
stages in fixed order: enrichment (0), structure (1), fingerprint (2), kind (3), card count (4),
card keys (5), label (6), placeholder gate (7), digit gate (8), canonical match (9), hint gate
(10), normalization (11). Each stage SHALL raise one named error from the ladder's code set
(`schema_violation`, `card_count_out_of_range`, `empty_label`, `label_too_long`, `non_cjk_label`,
`placeholder_label`, `digit_in_label`, `unknown_action_code`, `no_such_affordance`,
`unknown_target`, `hint_too_long`, `leak_detected`). Stage 6 SHALL reuse the exact
`world/ai/narrator.py` `_validate_has_cjk` logic; stages 7–8 SHALL be implemented in this module
as a generic `{...}` placeholder pattern and a mechanical ASCII-digit gate — narrator's own
placeholder regex is token-specific (`{actor}|{target}|{data[...]}`) and narrator has no digit
gate, so the card gates cannot be shared imports (schema design doc stage 6–8 amendment).

#### Scenario: A structurally invalid proposal fails at the structure stage
- **WHEN** the raw dict has keys other than the `OptionSet` fields
- **THEN** stage 1 rejects it with `schema_violation` before any later stage runs

#### Scenario: A label without any CJK codepoint is rejected
- **WHEN** a card label is ASCII-only
- **THEN** stage 6 rejects it with `non_cjk_label`

#### Scenario: A label carrying an ASCII digit is rejected
- **WHEN** a card label contains a digit, e.g. "3 個敵人"
- **THEN** stage 8 rejects it with `digit_in_label`

#### Scenario: A label echoing any template placeholder is rejected
- **WHEN** a card label contains a generic `{...}` token such as `{name}` or `{unknown}`
- **THEN** stage 7 rejects it with `placeholder_label` — unlike the narrator's token-specific
  placeholder rule, the card gate rejects every brace-token

### Requirement: Stage 9 enforces canonical replacement against the affordance vocabulary
For `known_action` cards, the model's `params` SHALL be treated as curation hints, never checked
for equality; stage 9 SHALL resolve `action_code` against the `affordances` argument and, on a
unique match, **unconditionally replace the card's params with that affordance's canonical
payload** so the validated card always satisfies `(action_code, params) == (affordance.action_id,
affordance.params)`. When several current affordances share `action_code` (e.g. one move entry
per exit), the model's typed params SHALL select the unique entry whose canonical params they
match — a hint, never a rejection against a single canonical — and a card whose params identify
no unique entry SHALL reject with `no_such_affordance` rather than guess. An `action_code`
outside the current affordances SHALL reject with `unknown_action_code` (unregistered) or
`no_such_affordance` (registered but not current). For `freeform` cards, stage 9 SHALL require
`action_code == "explore.talk_freeform"` and `params == {"npc_id": <int>}` equal to a freeform
affordance's bound target; the matched freeform affordance SHALL itself carry exactly the binding
shape, and the validated card's params SHALL remain exactly `{"npc_id": <int>}`. The freeform
card's `{npc_id}` params are the single binding-only exception to the canonical-payload rule; the
full `validate_talk_freeform_payload` (which requires `speech`) runs only on the client-composed
dispatch payload (schema design doc §1).

#### Scenario: A valid-now known card passes with canonical replacement
- **WHEN** a card's `action_code` matches exactly one current affordance but the model typed
  params differing from the affordance's
- **THEN** stage 9 passes and the card's params are replaced by the canonical copy, never the
  model's

#### Scenario: A known card with omitted params passes
- **WHEN** a valid `known_action` card omits `params` entirely (allowed by the JSON contract)
- **THEN** stage 9 supplies the canonical payload and passes — equality is guaranteed on the
  result, not on the model's input

#### Scenario: A multi-entry code is pinned by the model's params
- **WHEN** several current affordances share `action_code` (e.g. two move exits) and the card's
  params equal exactly one entry's canonical params
- **THEN** stage 9 passes and the card's params become that entry's canonical payload

#### Scenario: An ambiguous multi-entry code fails
- **WHEN** several current affordances share `action_code` and the card's params identify no
  unique entry (omitted or non-matching params)
- **THEN** stage 9 rejects it with `no_such_affordance` — the ladder never guesses which
  affordance the model meant

#### Scenario: A globally-allowed but not-current affordance fails
- **WHEN** a card names an action that exists in `ACTION_CODE_ALLOWLIST` but is not in the
  current `affordances` argument
- **THEN** stage 9 rejects it with `no_such_affordance`

#### Scenario: A freeform card binding an unknown target fails
- **WHEN** a `freeform` card carries an `npc_id` that no freeform affordance binds
- **THEN** stage 9 rejects it with `unknown_target`

#### Scenario: A freeform card's params stay exactly the binding shape
- **WHEN** a `freeform` card is validated against a bound freeform affordance
- **THEN** the validated card's params equal exactly `{"npc_id": <int>}` — never a copy of the
  affordance's params, so extra fields cannot smuggle past the binding contract

### Requirement: Leak gates apply to model-visible text only and expose no hidden values
The ladder SHALL apply the leak predicate to `label` and `hint` only — against the caller-supplied
`leak_blocklist: frozenset[str]` parameter of `validate_optionset` (numeric literals and hidden
trait keys of the deterministic view; default empty frozenset keeps the function total and pure)
plus the placeholder and digit gates; `params` are never leak-checked (after stage 9 they are
canonical copies or the freeform binding). The hinted categories SHALL be rejected: true-trait
numbers, raw affinity numbers, values that differ between `disguised_stats` and true traits, and
tokens not present in the bounded public context.

#### Scenario: A hint leaking a true-trait number is rejected
- **WHEN** a hint contains a numeric literal that appears in the caller's `LEAK_BLOCKLIST`
- **THEN** the stage-10 gate rejects the card with `leak_detected`

#### Scenario: Params are exempt from the blocklist
- **WHEN** a params value is an ordinary opaque id that happens to equal a blocklist token
- **THEN** no leak rejection fires — the gates never inspect `params`

### Requirement: Enrichment injects caller-side fields before validation
The module SHALL provide an enrichment helper that, given the raw LLM card dicts, injects the
caller-supplied `fingerprint`, sets `status` to `"ready"`, and defaults every `freeform` card's
`action_code` to the constant `"explore.talk_freeform"`, producing the enriched payload the ladder
validates. The `{npc_index}` → `{npc_id}` binding resolution is owned by `action-options-layer`;
this change's fixtures feed already-resolved `{"npc_id": int}` params.

#### Scenario: Freeform cards receive the fixed action code automatically
- **WHEN** a raw LLM `freeform` card without an `action_code` is enriched
- **THEN** its `action_code` becomes `"explore.talk_freeform"` and the enriched card passes stage 9
  when its `npc_id` is bound

### Requirement: The LLM JSON output contract is enforced by exact-field parsing
The module SHALL parse model output as inline `response_format` JSON (schema_id `action_options`),
matching the schema design doc §5: `known_action` cards carry `action_code`, `label`, optional
`params` and `hint`; `freeform` cards carry `npc_index`, `label`, optional `hint`; `fingerprint`
and `status` are caller-side and absent from model output. Parsing SHALL use the exact-field
parser pattern of `web/webclient/presentation/protocol.py`: unknown keys on a card are rejected,
and a wrong shape fails with a named rejection instead of being silently coerced.

#### Scenario: A model payload with an unknown key is rejected
- **WHEN** a card dict contains an extra key such as `"target"` or `"score"`
- **THEN** parsing rejects the card rather than ignoring the key
