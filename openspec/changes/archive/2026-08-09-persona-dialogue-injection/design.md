# persona-dialogue-injection — Design

## Context

The persona-store change (companion change in this plan) delivers `PersonaStore` mounted on
`LivingEntity.persona`, flattening `personality` / `life_story` / `habit` into one bounded labeled
block. The NPC dialogue layer (`world/ai/npc_dialogue.py`) builds deterministic system/user
messages: the system message renders `npc_dialogue.system` from the prompt library with
`{name}`/`{desc}`/`{location}`, and the user payload carries the player's identity,
`disguised_stats`, an optional affinity block, and bounded chat memory. The per-call no-leak
semantic validator (`_make_no_affinity_leak_validator`) binds the affinity value and cap and
rejects/retries/degrades any reply echoing them.

This change feeds persona into that existing pipeline and extends the secret set:

- NPC persona → system message (in-character role material).
- Player persona → user payload `player.persona` (the NPC recognizes its partner).
- Secret set → affinity value/cap plus true trait values under an active disguise.

Constraints:

- `world/ai/` never imports typeclasses or writers; persona blocks and secrets are computed
  read-only in `typeclasses/npcs.py` and passed through the existing context.
- Identical input must produce byte-identical prompts; persona absence must produce today's exact
  output.
- No new transport, schema, degradation path, or player-facing surface.

## Goals / Non-Goals

**Goals:**

- Inject NPC and player persona blocks through the prompt library.
- Generalize the no-leak validator to a bounded secret-set factory without changing affinity
  behavior.
- Keep offline degrade (greeting/silence) and guardrail retry semantics identical.

**Non-Goals:**

- Any content filtering of persona (authored content is opaque; leak protection is output-side).
- Persona use in Narrator, ScenarioDirector, or scene prompts.
- Any affinity, party, or intent behavior change.

## Decisions

### D1: Injection shape — system placeholder + user payload block

- `npc_dialogue.system` gains a `{persona}` placeholder positioned in the YAML so that an empty
  substitution reproduces the pre-persona system message; `_system_message()` always renders it,
  passing the flattened block when one exists and an empty string when not — the renderer never
  leaves a literal `{persona}` token and the byte-identical baseline holds by construction.
- The user payload gains `player.persona` beside `player.affinity` when the speaking player has a
  flattened block; `build_npc_dialogue_prompt()` accepts `npc_persona: str | None` and
  `player_persona: str | None`.
- Alternatives considered: omitting `persona` from the render call when absent. Rejected: the
  template would retain a literal `{persona}` token (or a KeyError would occur), breaking both the
  render contract and the byte-identical baseline. Always-pass-with-empty is the only shape
  consistent with both contracts.

### D2: Secret-set factory, affinity unchanged, installed whenever non-empty

`_make_no_affinity_leak_validator(value, cap)` generalizes to
`_make_no_leak_validator(secrets: frozenset[str])`; the affinity call site keeps binding exactly
its own value and cap (existing tests unchanged). The calling typeclass builds the set as plain
decimal strings: affinity value/cap when an affinity context exists, plus the true current `.value`
of `atk_phys`, `agility`, `defense`, `magic_level`, and `hp` (for `hp`, the current gauge value,
not the maximum) when `disguised_stats` exists and differs for that key. The set is passed to the
guarded entry point as an independent plain-value parameter, and the validator SHALL be installed
whenever the set is non-empty — including calls with no affinity context, so a disguised NPC's
true values are protected even against a player with no record. All secrets normalize like today's
affinity check (NFKC fullwidth folding) and are bound per call through the request descriptor so
interleaved calls never cross-contaminate.

- Alternatives considered: gating the validator on affinity-context presence (today's behavior).
  Rejected: it would leave disguise secrets unprotected for recordless players — a real leak path
  surfaced by review.

### D3: Read-only wiring through `at_talked_to`

`LLMNPC.at_talked_to` / `run_npc_exchange` compute, read-only:

- `self.persona.flatten()` for the NPC block;
- `character.persona.flatten()` for the player block;
- the disguise secret set from the NPC's own `disguised_stats` vs true traits (an NPC reads its
  own true values; the player never sees them), converted to decimal strings;

and pass them through the existing context into `world/ai/npc_dialogue.py`, mirroring how the
affinity context flows today. `world/ai/` continues to receive plain values, never entities, and
performs only NFKC-folded string matching on the secrets.

### D4: Prompt-library registry

`PromptSpec("npc_dialogue.system", "npc_dialogue.yaml", ("name", "desc", "location"))` gains
`persona` in its allowlist; `prompts/npc_dialogue.yaml` gains the `{persona}` token with authored
instruction text. `render_prompt` semantics are unchanged.

## Risks / Trade-offs

- [Persona text could leak secrets into the prompt input] → Accepted by design (P3: authored
  content is not filtered); the output-side validator is the guard, and it now also covers true
  trait values under disguise.
- [Larger prompts raise token cost] → The flatten block is capped in `PersonaStore`; the user
  payload's serialization bounds already apply.
- [Overlapping secret numbers (e.g. a true trait equals affinity value) cause redundant
  bindings] → A set deduplicates; behavior is unchanged otherwise.
- [The `{persona}` token could collide with authored template braces] → render_prompt's exact
  `{token}` matching and the registry validation reject unknown tokens, per the prompt-library
  contract.

## Migration Plan

No data migration. The prompt text and allowlist change together; a stale prompt file would be
rejected by the loader's placeholder validation (fail that key, deterministic game still
playable).

## Open Questions

- None blocking. Whether the player persona block should be suppressed for disguised players is
  deferred; the prompt template is the seam.
