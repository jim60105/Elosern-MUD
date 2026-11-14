# world/

Everything that is game logic or game data and is not a command or a typeclass.
Each package has one ownership role. The role decides what code in it may do.

| Package | Role | What it holds |
| --- | --- | --- |
| `rules/` | **Writer** (the general deterministic engine) | Action resolution, combat, time, movement, economy, guild, party, dialogue, titles, and the read models built on them. Guide: `rules/AGENTS.md`. |
| `maps/` | **Writer** of room, instance and monster-population lifecycle | The published map world, wilderness, monster sites and regional population. Guide: `maps/AGENTS.md`. |
| `quests/` | **Writer** of quest lifecycle | Quest definitions, runtime records, scene packages, escort and deadline settlement. |
| `narrative/` | **Writer** of persistent narrative state | Events, memory, recall, threads, letters, dream sessions, context snapshots. Guide: `narrative/AGENTS.md`. |
| `art/` | **Writer** of art records | Subjects, queue, worker boundary, asset store, presenter primitives. `service.py` is the only module that writes asset and queue records; `gallery.py` owns the gallery records. |
| `lore/` | **Read-only registry** | Frozen dataclasses for races, items, monsters, anchors, economy, guild ranks, monster placement and activity. |
| `skills/` | **Read-only registry** plus handlers | Skill and equipment definitions (`registry/`), narration data, the skill and equipment handlers. |
| `prompts/` | **Read-only registry** | The key, placeholder allowlist and length bound of every LLM prompt. The text itself is in the top-level `prompts/` folder. |
| `ai/` | **Proposal only** | LLM client, guardrail and one module per generative layer. Never applies a state change. Guide: `ai/AGENTS.md`. |
| `imports/` | Import boundary | External world and character import: validate everything, then persist all or nothing. |
| `observability/` | Log facade | `log_debug`, `log_info`, `log_warn`, `log_error`, and the LLM transcript. The only place that may touch a logger. |
| `tests/` | Shared test support | `synthetic_data/` (the stand-in game world for behavior tests) and map fixtures. |

Rules that follow from the roles:

- A state change is applied by a **writer** package. A registry package and
  `ai/` route every mutation through `rules/` (or the owning writer).
- A consumer reads a number from its registry or rulebook. It never copies the
  number into its own module.
- A subpackage needs an `__init__.py`. A test module needs a CI owner:
  `uv run --locked python -m tools.shard_register fix`.

The architectural reasons are in the root `AGENTS.md`, section
"Architectural invariants".
