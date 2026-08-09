# persona-dialogue-injection — Tasks

## 1. Prompt library

- [ ] 1.1 Add `persona` to the `npc_dialogue.system` `PromptSpec` allowlist in
      `world/prompts/registry.py`
- [ ] 1.2 Update `prompts/npc_dialogue.yaml` with a `{persona}` token positioned so that an empty
      substitution reproduces the current system message byte-for-byte, plus authored instruction
      text that reads naturally when the block is present (the NPC speaks in character from the
      supplied persona)
- [ ] 1.3 Update prompt-library tests: `persona` placeholder substitution, empty-`persona`
      substitution (no literal token left, no error), allowlist rejection for unknown value names

## 2. Dialogue prompt construction

- [ ] 2.1 Extend `_system_message(npc_context)` in `world/ai/npc_dialogue.py` to always render
      `persona` through `render_prompt("npc_dialogue.system", ..., persona=_cap_string(npc_persona
      or ""))` — never leaving a literal `{persona}` token
- [ ] 2.2 Extend `build_npc_dialogue_prompt(...)` with `npc_persona: str | None` and
      `player_persona: str | None`; serialize `player.persona` beside `player.affinity` only when
      present; keep byte-identical output when absent

## 3. No-leak validator generalization

- [ ] 3.1 Generalize `_make_no_affinity_leak_validator(value, cap)` to
      `_make_no_leak_validator(secrets: frozenset[str])`; keep the affinity call site binding
      exactly its value and cap (existing tests unchanged)
- [ ] 3.2 Keep NFKC fullwidth folding, per-call binding through the request descriptor, retry,
      and exhaustion-degrade semantics identical

## 4. Seam wiring

- [ ] 4.1 In `typeclasses/npcs.py`, compute read-only persona blocks
      (`self.persona.flatten()` / `character.persona.flatten()`)
- [ ] 4.2 In `typeclasses/npcs.py`, build the secret set as plain decimal strings: affinity
      value/cap when an affinity context exists, plus the true current `.value` of
      `atk_phys`/`agility`/`defense`/`magic_level`/`hp` (hp at its current gauge value, not the
      maximum) for each disguise key that differs
- [ ] 4.3 Pass the secret set as an independent plain-value parameter to the guarded entry point;
      install the no-leak validator whenever the set is non-empty (not gated on affinity
      presence); confirm `world/ai/npc_dialogue.py` still imports no typeclass or writer module

## 5. Tests

- [ ] 5.1 `FakeLLMClient` dialogue tests: NPC persona present/absent, player persona
      present/absent, byte-identical baseline, capped blocks
- [ ] 5.2 No-leak tests: reply echoing a disguised true value rejects/retries; speech containing
      the disguised value passes; the leak check fires without any affinity record (disguised NPC
      vs recordless player); `hp` protected at its current gauge value (`hp.value != hp.max`);
      no-disguise keeps affinity-only binding (or no validator when the set is empty); per-call
      isolation; exhaustion degrades without presenting the number
- [ ] 5.3 Read-only assertions: persona records byte-identical after prompt builds; prompt module
      import-surface contract test stays green

## 6. Traceability and verification

- [ ] 6.1 Annotate discoverable tests with `covers_requirement` using canonical IDs from
      `uv run --locked python -m tools.spec_traceability list`
- [ ] 6.2 Run `uv run --locked python -m tools.spec_traceability check` and confirm the new and
      modified requirements are covered
- [ ] 6.3 Run the focused test packages (world/ai tests, typeclasses dialogue tests, prompt
      library tests) and confirm green
