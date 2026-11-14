# world/ai guide

The generative layer. Code here asks a model for text and returns a validated
**proposal**. It never applies a state change, under any circumstance.

The game must stay fully playable with every LLM and image service offline. So
every layer has a deterministic fallback, and no deterministic rule waits for a
model.

## The three-part shape of every feature

1. **A layer in `world/ai/`** builds the prompt, calls `guardrail.guarded_call`
   and returns a frozen proposal value (or the fallback). It imports no state
   writer, no live transport and no socket;
   `tests/test_ai_transport_contract.py` enforces this.
2. **A composition root in `server/*_service.py`** (`ai_director_service.py`,
   `dream_service.py`, `scene_flavor_service.py`, `title_nomination_service.py`,
   `correspondence_service.py`) wires the layer to the real client and hands
   the proposal to the owner.
3. **A deterministic owner** (`world/rules/`, `world/quests/`,
   `world/narrative/`) validates the proposal again and applies it, or
   rejects it.

If you find yourself writing to `obj.db`, a model or a handler inside
`world/ai/`, stop: that code belongs in step 3.

## Find the owner

| You are changing | Modules |
| --- | --- |
| HTTP transport and payload | `client.py` (`OpenAICompatClient`), `errors.py` |
| Endpoint, model, timeouts, token limits per layer | `profiles.py` (`LLMProfile`, read from the `LLM_PROFILES` setting), `server/conf/llm_knobs.py`, `docs/development/llm-configuration.md` |
| Validation, retry, degrade | `guardrail.py` |
| Output JSON schemas | `schemas/` |
| Combat and action prose | `narrator.py` |
| NPC replies and intents | `npc_dialogue.py` (the intent is verified and applied by `world/rules/npc_intents.py`) |
| Generated quests | `scenario_director/`, `director_templates.py` (the offline template pool) |
| Story beats | `story_director/` |
| Dream collaboration | `dream.py` |
| Scene atmosphere text | `scene_flavor.py` |
| Character concept to creation proposal | `character_creation.py` |
| Letters | `correspondence.py` |
| Epithet nomination | `title_nomination.py` |
| Test double | `fake_client.py` (`FakeLLMClient`) |

## How code here is written

- **Prompt text is data.** It lives in the top-level `prompts/*.yaml`. Its key,
  placeholder allowlist and length bound are declared in `world/prompts/`.
  Render with `world.prompts.loader.render_prompt`; never write prompt prose in
  Python. Changing a prompt means editing the YAML and, if the placeholders
  change, its spec in `world/prompts/registry.py`.
- **Every call goes through `guarded_call`.** It resolves the layer profile,
  validates the reply against the declared schema and every registered
  semantic validator, retries with the errors appended, and degrades to the
  registered fallback. Register hooks with `register_semantic_validator` and
  `register_degrade_fallback`; do not edit the pipeline for one layer.
- **A new layer registers a degrade fallback.** A layer without one fails with
  `NoDegradeFallbackError`. The fallback must be a legal, playable result.
- **Profiles are validated at construction and never clamped.** A bad bound
  raises at startup naming the layer and field. Do not add a silent default.
- **Proposals carry values only**: frozen dataclasses of plain data, no object
  references and no callables.
- **Logs stay bounded.** The operational log gets one `llm_call` event per
  call with a `call_id`. Full prompts and replies go to the transcript
  (`world/observability/transcript.py`, `server/logs/llm/`). Credentials never
  enter either.
- **In-world knowledge boundaries still apply.** A prompt may contain only
  what the speaking character is allowed to know. The no-leak validators in
  `npc_dialogue.py` are part of the contract, not an optimisation.

## Tests

- Never call a live model, Stable Diffusion or the network. Use
  `FakeLLMClient`: it replays fixtures by request matcher and can script a
  timeout, an HTTP error, a connection error and a non-JSON body.
- Test three paths for a layer: a valid reply, a reply that fails validation
  until the retry budget is spent, and a transport failure. The last two must
  end in the fallback.
- One module is one label:
  `uv run --locked --env-file=.env.evennia-test evennia test --settings test_settings.py --keepdb world.ai.tests.<module>`

## Mistakes that have happened here

- An endpoint returned `content: null` and the layer raised instead of
  degrading. Treat every field of a model reply as possibly missing.
- A long-output layer hit its wall-clock budget. Budgets are per layer in the
  profile; widen the one layer, not the shared default.
- HTTPS endpoints failed because Twisted TLS support was not installed. Add
  dependencies with `uv add`, never by editing `uv.lock`.
- A background reply arrived after the player had moved on and was applied
  anyway. A composition root accepts a reply only while its original owner and
  outstanding request still match.
