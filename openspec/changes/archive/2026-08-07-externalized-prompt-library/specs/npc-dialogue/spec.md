## MODIFIED Requirements

### Requirement: NPC dialogue prompts are deterministic, bounded, and inject disguised stats

`build_npc_dialogue_prompt(...)` SHALL produce a deterministic system/user message pair serialized from the NPC's identity (name, description, location), the speaking player's identity and `disguised_stats`, and a bounded chat-memory window, using stable JSON serialization with hard bounds on memory lines, per-field string length, and total size. The system message SHALL be rendered from the prompt library's `npc_dialogue.system` key via `render_prompt("npc_dialogue.system", name=…, desc=…, location=…)` — the library is the sole source of the system-prompt template, and the module SHALL NOT embed it as a Python constant; only the allowlisted `{name}`, `{desc}`, and `{location}` placeholders are substituted. The system message SHALL fix the NPC's role, the 正體中文 language, and the output contract: reply with a `{speech, intent}` object, never invent outcomes, and express only what the NPC could perceive — including reading the player's `disguised_stats` as the truth. Identical input SHALL produce byte-identical prompts with no live entity references.

#### Scenario: A disguised elf reads as weak to the NPC
- **WHEN** a prompt is built for an NPC facing a player whose `disguised_stats` hide their true power
- **THEN** the prompt carries the disguised values so the model describes the player as the NPC perceives them, not the player's true traits

#### Scenario: Identical input yields byte-identical prompts
- **WHEN** the same NPC identity, player data, disguised stats, and memory are serialized twice
- **THEN** both prompts are byte-identical and contain only plain JSON-compatible data with no live entity references

#### Scenario: Oversized memory is bounded deterministically
- **WHEN** the chat memory exceeds the configured window
- **THEN** the prompt truncates to the fixed window with an explicit marker and never produces an unbounded request

#### Scenario: The system message is rendered from the prompt library
- **WHEN** the NPC dialogue system message is inspected
- **THEN** it equals `render_prompt("npc_dialogue.system", name=…, desc=…, location=…)` and the prompt-library file is the only place its template text is defined
