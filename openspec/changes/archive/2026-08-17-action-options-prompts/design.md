## Context

The pipeline design doc (§3, §5) specifies the prompt contract and profile slot for the
action-options layer: `prompts/action_options.yaml` with `system`/`user` keys whose placeholders
match the `ActionOptionsContext` fields, and an `action_options` slot in `LAYER_NAMES` whose
profile requires `supports_response_format: true`. The prompt repo already validates every key
against code-declared allowlists (`world/prompts/registry.py`, loader) and the profiles module
already fails closed on every bound (`world/ai/profiles.py`). This change extends both registry
surfaces — no behavior change outside the generative layer.

## Goals / Non-Goals

**Goals:**
- Ship the action-options prompt text under the exact loader contract (keys, allowlist, bounds).
- Add the `action_options` layer slot with defaults tuned for a 5-card JSON payload.
- Fail closed at startup if the slot's structured-output requirement is disabled.

**Non-Goals:**
- The context serializer, `{npc_index}` binding, and `world/ai/action_options.py` generation logic
  (`action-options-layer`).
- Changes to settings files (the `default_profiles()` source already propagates the slot).
- Any new prompt key beyond the two documented ones.

## Decisions

- **Two keys in one file**, matching `art.yaml`'s multi-key precedent, with **split allowlists**:
  `action_options.system` carries an empty allowlist (static role/hard-rule text — a context token
  accidentally placed there must fail loading), and `action_options.user` allowlists exactly the
  seven `ActionOptionsContext` fields, so `render_prompt` can substitute the serialized block per
  field and a typo fails loading.
- **Plain-text hard rules in the system prompt**, enforced twice downstream: the deterministic
  ladder (change `action-options-schema` stage 7/8/9) is the real gate; the prompt text is the
  cheap first line of defense and the player-visible contract for offline review.
- **Per-layer required flag in `world/ai/profiles.py`:** a small constant map
  (`REQUIRED_PROFILE_FLAGS = {"action_options": {"supports_response_format": True}}`) checked in
  `build_profiles` after `validate_profile_values`, naming layer and field in the raised
  `ProfileValidationError`. Generic bounds stay untouched so no other layer changes behavior.
- **Startup enforcement in `server/conf/settings.py`:** `build_profiles` is otherwise reached only
  lazily through `get_profile`, so a misconfigured `LLM_PROFILES` would fail on the first live
  call, not at startup. The settings module therefore validates the map at import time with one
  explicit `build_profiles(LLM_PROFILES)` call placed **after every settings override**, including
  the `secret_settings` block at the end of the module — so a misconfigured slot fails at startup
  even when it arrives through the documented override mechanism (rubber-duck R2), while the
  profile resolution path itself is untouched.
- **Defaults in `default_profiles()`** (`temperature` 0.7, `max_tokens` 320,
  `supports_response_format: true`, otherwise the shared locals-first shape) so the slot appears
  everywhere the default source is used, including `settings.LLM_PROFILES`.
- **Verification only for settings:** the settings module already calls `default_profiles()`;
  a test asserts the effective profile, with no settings diff.

## Risks / Trade-offs

- **Prompt drift:** the system-prompt hard rules duplicate constraints the ladder enforces.
  Accepted: the ladder is authoritative; the prompt improves first-attempt yield, and a parity
  test asserts the placeholders stay in sync with the context fields.
- **max_tokens estimate (320):** sized for ~5 cards × short JSON; if a future context kind
  carries longer labels, the profile bound must be revisited — pinned via test only, no dynamic
  sizing in v1.
- **Stricter profile rule is additive:** existing deployments with `supports_response_format:
  false` for other layers are unaffected; only the new slot carries the requirement.
- **Layer-set contract:** adding the slot modifies the `llm-profiles` main capability contract
  (its requirement text still enumerated the pre-`character_creation` set); the change carries a
  MODIFIED delta (`specs/llm-profiles/spec.md`) updating the registry requirement, and its tests
  re-annotate `covers_requirement` where the layer enumeration is asserted.