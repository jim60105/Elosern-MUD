# design — env-overridable-llm-profiles

## Context

`world/ai/profiles.py` today: frozen `LLMProfile` (10 fields), `validate_profile_values`,
`default_profiles()` reading `os.environ["OLLAMA_BASE_URL"]` directly, `build_profiles`,
`get_profile`. `server/conf/settings.py:237-239` imports `default_profiles()` and
validates the effective map at boot (line 421). `server/conf/test_settings.py` pops all
`ART_SD_*`/`ART_SCHEDULER_*`/`ELOSERN_VUE_CLIENT` names before importing production
settings. The inventory contract test (`server/conf/tests/test_env_overrides.py`) parses
`.env.example` keys and asserts each is an AST-extracted `os.environ` read in
`settings.py` or an entry of the reviewed `EXTERNAL_READERS` allow-list — currently
holding `OLLAMA_BASE_URL` (reader: `world/ai/profiles.py`).

Constraints: fail-closed boot errors (`_env_typed` naming variable/value/rule);
no backward compatibility (zero users); determinism; the follow-up change
`llm-endpoint-wire-configuration` owns request-body/header serialization, so this change
stores fields without changing any wire bytes (except the model name, already serialized).

## Goals / Non-Goals

**Goals:**
- One declarative knob table (in an inert shared module, D-A4) generating global
  `LLM_<SUFFIX>` and per-layer `LLM_<LAYER>_<SUFFIX>` variables for all 23 knobs of
  design §3.1 (184 generated names).
- `LLMProfile` stores all new fields, validated; `profiles.py` is env-free.
- `LLM_BASE_URL` replaces `OLLAMA_BASE_URL` across compose/.env.example/tests/docs.
- `secret_settings.py` gains per-layer merge semantics (D-A7) instead of whole-map
  replacement, honouring the per-layer precedence contract.
- Test-settings sanitization and the inventory contract move with the new names.

**Non-Goals:**
- Any change to `_format_request_body` / `_headers` / transport (follow-up change).
- Docs policy reversal for `LLM_API_KEY` (lands with the follow-up change that makes the
  key observable); this change only stores the key.
- `secret_settings.py` example files or new settings beyond the knob table.

## Decisions

### D-A1 The knob table is data, not code per knob

`server/conf/llm_knobs.py` (new, import-safe, zero environment reads — D-A4) defines
`LLM_KNOBS: tuple[LlmKnob, ...]`, one row per profile field (23 rows):
`(profile_field, env_suffix, kind, bounds, default_per_layer_overrides)`. Kinds map onto
the existing helpers: `str` (`_env_str`), `typed_float` / `typed_int` / `bool`
(`_env_typed` with bounds and rule text), `choice` (the `_env_choice` conversion as a
confirmed-present variant), plus a refactored shared core:

```python
def _env_validate(name, raw, convert, *, minimum=None, at_least=None, maximum=None,
                  multiple=None, rule):
    """Conversion/bound core shared with _env_typed: the raw is CONFIRMED-PRESENT
    (presence/blank handling stays with the caller), and the error quotes the
    unstripped raw value exactly as _env_typed always has."""
```

Building the raw profile dict loops `LLM_KNOBS × LAYER_NAMES` in `settings.py`: layer
value = per-layer env if present else global env if present else layer code default.
Resolution is presence-driven: a field enters the map only when some name carried a
non-blank raw, so unset optional knobs never overwrite the per-layer code defaults
(320/640 `max_tokens`) and land as `None` via the field default instead.
Rationale: 23 knobs × 8 names cannot be hand-written without drift. The AST inventory
test cannot see loop-constructed names (its extractor matches literal first-arguments
only — verified against `test_env_overrides.py::_env_read_names`), so generated names are
contract-checked through the inert module's pure `llm_env_names()` function, not AST
extraction (D-A4). Alternative considered: 184 literal calls; rejected as unmaintainable.

### D-A2 Optional `None` vs `""` distinction is structural

Optional strings (`api_key`, `app_title`, `app_url`) use the existing `_env_str` default
`""` — empty string *is* the omit sentinel (matches `ART_SD_SAMPLER` family semantics).
Optional numbers/tri-states need no dedicated optional helper because the resolver only
converts confirmed-present raws: absent/present-but-blank simply never enters the map and
the field default (`None`) applies — omit-by-absence, not omit-by-sentinel.
`reasoning_enabled` is therefore tri-state through presence alone: absent/blank →
`None`, a truthy/falsy word (existing word list) → `True`/`False`, anything else fails
closed. This keeps C-5's "None never serializes" expressible without a sentinel string
that could collide with real content.

### D-A3 `default_profiles(defaults=None)` injection shape

`defaults: Mapping[str, Mapping[str, Any]]` — full or partial per-layer dicts merged
over code defaults inside `default_profiles` itself. `settings.py` passes
`{layer: {field: value}}` for only the knobs that resolved from environment. Profiles.py
keeps zero `os.environ` imports (a grep-able contract, enforced by the existing
transport-boundary/contract style test or a direct assert). Rationale: keeps the
validator of *bounds* (profiles) and the validator of *env syntax* (settings) separate;
tests inject dicts, never patch `os.environ`.

### D-A4 Inventory contract and sanitize list follow an inert shared module

`test_settings.py` must pop env names *before* importing production settings, and the
inventory test's extractor is literal-only — neither can consume a name set that lives
behind a settings import. Fix: the knob metadata and one pure
`llm_env_names() -> frozenset[str]` (global ∪ per-layer, computed from `LLM_KNOBS` ×
`LAYER_NAMES`) live in `server/conf/llm_knobs.py`, which imports nothing but stdlib and
performs no environment reads.

- `settings.py` imports the module and publishes
  `LLM_ENV_NAMES = frozenset(llm_env_names())` (a derived export, not a second source).
- `test_settings.py` keeps its literal `_ENV_OVERRIDES` tuple for the ART/ELOSERN knobs
  (the AST `_ENV_OVERRIDES` extractor keeps working) and additionally pops
  `llm_env_names()` imported from the inert module — the loop variable is separate; the
  inventory test's popped-names extractor is updated to the union of the literal tuple
  elements and the inert-module evaluation.
- The inventory test asserts `.env.example`'s active `LLM_*` global keys equal the global
  subset of `llm_env_names()` **as exact set equality** (no cardinality assertions), and
  asserts `settings.LLM_ENV_NAMES == llm_env_names()` after settings load.
- `.env.example` gains all 23 global names (commented, per-knob format) plus two
  per-layer examples (`LLM_CHARACTER_CREATION_MODEL`, `LLM_ACTION_OPTIONS_MAX_TOKENS`)
  documented in prose rather than 184 entries. Per-layer names are covered by the
  documented suffix grammar, not listed (same way the test does not enumerate compose
  interpolation secrets today).
- `EXTERNAL_READERS`: remove `OLLAMA_BASE_URL`.
- Rationale: one inert source of truth for "which names are env-backed", consumable
  pre-settings by test bootstrap, by the inventory contract, and by `settings.py` itself.

### D-A5 New field bounds (single home: `validate_profile_values`)

| field | bound |
|---|---|
| `api_key`, `app_title`, `app_url` | `str` only (any content legal; `_normalize_headers` untouched) |
| `frequency_penalty`, `presence_penalty` | finite float, `-2..2` inclusive |
| `top_p` | finite float, `0 < x <= 1` |
| `top_k` | positive int |
| `repetition_penalty` | finite float, `x > 0` |
| `min_p` | finite float, `0 <= x <= 1` |
| `top_a` | finite float, `x >= 0` |
| `reasoning_enabled` | `bool` or `None` |
| `reasoning_effort` | `None` or member of `("minimal","low","medium","high")` |
| `reasoning_style` | member of `("openrouter","vllm","off")` |
| `max_completion_tokens` | `None` or positive int |

`api_key` uses `dataclasses.field(repr=False)` and a test asserts `repr(profile)` and
`str(profile)` exclude the value. `LLMProfile` keeps `frozen=True`; the new fields carry
defaults so every existing constructor call site (tests, services) keeps working
unchanged.

**Credential smuggling through `headers` is rejected at construction** (`_normalize_headers`
gains a case-insensitive deny set: `authorization`, `proxy-authorization`, `x-api-key`,
`api-key`; error names layer/field and points at `api_key`). The dataclass `repr` includes
the headers mapping, so a bearer value smuggled into `headers` would defeat the
`repr=False` exclusion — fail-closed rejection keeps `api_key` the single credential
route. `X-Title`/`HTTP-Referer` and every non-credential header stay settable. This is
the profile-side half of the follow-up wire change's key-secrecy requirement; it is
phased here because the validator lives in profiles.py.

### D-A6 Wire bytes are frozen until the follow-up

`_format_request_body` and the headers path are not touched. The only observable request
change under this change is `model` (and `temperature`/`max_tokens`/etc.) flowing from env
as they already flow from the profile. A regression test asserts the byte-exact body with
no knobs set, guarding the C-5 "today's payload unchanged" property against accidental
serialization creep during D-A1 refactors.

## Risks / Trade-offs

- [AST inventory test cannot see env reads built from loop-constructed names] → the knob
  table lives in the inert `server/conf/llm_knobs.py` and the contract runs through its
  pure `llm_env_names()` (exact set equality against `.env.example` globals + the
  published-set identity check), not AST extraction. Belt: the sanitize loop pops exactly
  `llm_env_names()`, so a name missing from the table cannot poison tests either.
- [`default_profiles` signature change breaks call sites] → keyword-only with default
  `None`; repo grep shows test helpers (`_raw()` in five test modules) call it with no
  args — they keep working; the env-patch tests (`test_profiles.py:212`) move to
  injection instead of `patch.dict(os.environ, ...)`.
- [`secret_settings.py` whole-layer replacement silently drops env overrides] → fixed by
  D-A7 per-layer merge; a one-layer secret file can no longer discard the other six
  layers' environment-resolved values.
- [Two-change split leaves `api_key` stored-but-unused for a window] → acceptable: no
  user-visible surface claims key support until the wire change lands; the docs policy
  reversal also lands there, so no half-documented secret.

### D-A7 secret_settings merges per layer, over the env-resolved map

Today `LLM_PROFILES` is one setting and `from secret_settings import *` replaces the
whole map, so a secret file carrying a single layer silently loses the other six layers'
environment configuration (the duck review's blocker). New mechanism in `settings.py`:

1. Resolve the full env-aware raw map (`_ENV_RESOLVED_LLM_PROFILES`, module-private copy
   taken **before** the `secret_settings` import).
2. After the import, if `secret_settings` defined `LLM_PROFILES`, merge it **per layer**:
   `LLM_PROFILES = {layer: dict(secret_entry) if layer in secret_map else
   _ENV_RESOLVED[layer] for layer in LAYER_NAMES}` — a supplied secret entry replaces
   that layer wholesale (no field merge, matching the "wholesale" documentation), every
   other layer keeps its environment-resolved entry.
3. `build_profiles(LLM_PROFILES)` validates as today. A secret entry naming an unknown
   layer still fails closed via `build_profiles`.

Covered by a subprocess settings-import test: global + one unrelated per-layer env values
plus a one-layer secret map → unaffected layers keep env values; the secret layer takes
only its entry's fields.
