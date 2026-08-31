# Design: art-generation-config-parity

## Context

`world/art/sd_worker.py` is the MUD's internal, synchronous, deadline-bounded
sd-webui client (single-worker drain, Twisted thread, fake seam for tests).
The HeartReverie `sd-webui-image-gen` plugin is a mature reference with the
same API target (A1111/Forge `/sdapi/v1/*`); it is settings-UI-driven
(JSON-schema config), TypeScript/Deno, and browser-facing — so only its API
contract, field shapes, and semantics transfer, not its architecture.

Reference facts this design locks in (source-verified in
`lib/client.ts`, `lib/generation.ts`, `handler.ts`):

- Option endpoints and item-field fallbacks: `sd-models` → `title ??
  model_name`; `samplers` → `name`; `schedulers` → `label ?? name`;
  `prompt-styles` → `name`; `sd-modules` → `model_name` (Forge-only endpoint).
- Auth: `Authorization: Basic btoa(user:pass)` sent when username is set.
- Generation result: `images[0]` base64 + JSON-parsed `info.seed ?? 0`.
- `override_settings` companions: `sd_model_checkpoint` for the checkpoint;
  `forge_additional_modules` (list) plus the fixed
  `forge_unet_storage_dtype: "Automatic (fp16 LoRA)"` for modules.
- Reference always restores-afterwards and forces `samples_format: "png"`
  (we already do exactly this).

## Goals / Non-Goals

**Goals:**

- Parity with the reference's server-facing capabilities: enumeration, auth,
  seed capture, styles/modules freedom.
- Keep every hardening property we already have that the reference lacks:
  total-deadline transport, response/size caps, PNG validation, named
  `SDError` taxonomy, never-followed redirects, fake-client determinism.
- Enumeration is a **staff diagnostic surface**, not a runtime mutation path
  (single-writer invariant: only `@art options` reads, never writes).

**Non-Goals:**

- The reference's SSRF host allowlist (`allowedHostPatterns`) and DNS
  resolve-and-pin (`resolveAndPinHostnames`). The reference guards a
  user-editable URL field on an editor server; here the URL comes only from
  operator-controlled settings/env in a single-player local product, scheme is
  allow-listed and redirects are never followed. Adopting the allowlist would
  add failure modes without a threat model. Documented as rejected.
- `/queue/status` (reference exposes it; we surface queue state through
  `@art status` records instead — no gradio-version coupling).
- A settings **UI**: the MUD has no admin web UI; parity is achieved on the
  staff command surface + settings files, which is this project's idiom.
- Changing txt2img request semantics — the audit confirmed them; untouched.

## Decisions

### D1 — Enumeration reuses the bounded transport with fixed private caps, verbatim names

A private `_list_options(path, *, item_keys, max_items=_OPTIONS_MAX_ITEMS, timeout_seconds=_OPTIONS_TIMEOUT_SECONDS)`
GETs via the transport core and requires a JSON **list** of at most 100 items,
each a dict; the caps are module constants (`_OPTIONS_MAX_ITEMS = 100`,
`_OPTIONS_TIMEOUT_SECONDS = 10.0`) and the five public wrappers
(`list_models/list_samplers/list_schedulers/list_styles/list_modules`) accept
no parameters, so the 100-item and 10-s bounds are enforced invariants, not
caller-adjustable defaults. Per item the helper extracts the first present
string among the reference fallbacks for that endpoint; a list member that is
not a dict or carries no string fallback value is `sd_malformed_response`
(never a silent drop); a selected string is tested for emptiness via `strip()`
and dropped when empty, otherwise returned **verbatim** (unstripped) — the
command's purpose is exact copy/paste of server names. Violations raise only
the existing named errors (`sd_http_error`, `sd_timeout`,
`sd_malformed_response`, `sd_response_too_large`) — no new error taxonomy.
GET requests omit `Content-Type` (cosmetic parity nit noted in the audit;
matches "GET has no body type" correctness). `_http_json` gains a
`timeout_seconds: float | None = None` parameter (default = the existing
setting); the deadline and every refreshed socket timeout derive from that
budget.

### D2 — Auth settings are secret-file-only plain settings

```python
ART_SD_USERNAME = ""
ART_SD_PASSWORD = ""
```

Defined **without** any `_env_*` helper (like `ART_SD_CLIENT`/
`ART_STORE_ROOT`, with the same "deliberately NOT environment-overridable"
comment), documented as sanctioned `secret_settings.py` keys. Rationale: the
env-overridable capability requirement enumerates the env-backed set exactly;
adding credentials to the environment would contradict the existing
`secret_settings.py` invariant (secrets never in env) and the `.env.example`
inventory's "no secrets" guarantee. The AST inventory guard test gains the two
names to its never-env-read list alongside `ART_SD_CLIENT`/`ART_STORE_ROOT`.

The client adds `Authorization: Basic` **iff both** `ART_SD_USERNAME` and
`ART_SD_PASSWORD` are non-empty. Rationale: the reference is split —
`handler.ts` constructs the auth object only when both are set, while
`client.ts` gates on username alone; requiring both is the reference's
effective end-to-end behavior and gives one unambiguous rule here. A username
with an empty password sends no header and is documented as a
misconfiguration. The password value never appears in any log line or error
message; tests assert redaction.

### D3 — `GeneratedImage` dataclass; seed validated defensively, never job-fatal

```python
@dataclass(frozen=True)
class GeneratedImage:
    data: bytes          # PNG bytes (existing caps/validation)
    seed: int | None     # from response info.seed, or None
```

`generate()` returns `GeneratedImage`. Seed parsing: `response["info"]` may be
missing, non-JSON, or lack `seed`; any of those yields `None` (a seedless image
is still a perfectly good image). A JSON `seed` must be a non-negative integer
— bool rejected, floats rejected — else `None`. The worker settles
`done` with `record.db.seed = seed` (nullable `AttributeProperty(default=None)`
on `ArtAssetRecord`). `@art status` appends ` seed=<n>` only when present.
`settle_generated` signature grows `seed: int | None = None` keyword.

Both fakes (`world/art/fake_sd_client.py`,
`web/tests/browser/fake_sd_client.py`) return `GeneratedImage(DEFAULT_PNG,
seed=12345)` with scripted-seed support; `worker.py` `_settle_one` uses
`image.data`/`image.seed`.

### D4 — Styles/modules knobs: free-text CSV, exact pass-through, reference companions

```python
ART_SD_STYLES = _env_str("ART_SD_STYLES", "")    # "style A, style B"
ART_SD_MODULES = _env_str("ART_SD_MODULES", "")  # "TE.safetensors, vae.safetensors"
```

Parsed at request build into `list[str]` with per-item strip and empty-item
drop; empty result ⇒ field **omitted** from the body (like sampler today).
`ART_SD_STYLES` → body `styles: [...]`. `ART_SD_MODULES` →
`override_settings.forge_additional_modules = [...]` **plus**
`forge_unet_storage_dtype: "Automatic (fp16 LoRA)"` (exact reference constant).
Names are free text, no validation beyond non-empty after strip: style/module
typos must surface as the server's own HTTP error (reference does the same),
not be invented client-side. `@art options styles|modules` exists precisely so
staff copy exact strings. Documented: `modules` targets **Forge** forks; on a
plain A1111 server Forge ignores unknown override keys (harmless) or 400s —
documented behavior, not enforced.

Alternative considered: JSON-list env syntax — rejected; the existing
free-text idiom (`ART_SD_CHECKPOINT` etc.) and `.env.example` single-line
style favor CSV with documented exact-match semantics.

### D5 — `@art options` is a read-only staff diagnostic off the reactor

`CmdArtOptions(_ArtCommand)` (Developer lock), arg one of
`models|samplers|schedulers|styles|modules`. The enumeration is dispatched
with `twisted.internet.threads.deferToThread` and the reply is sent from a
reactor callback — never inline on the reactor thread (the command `func` IS
the reactor; a synchronous bounded stall still freezes every session, which
the established `worker.drain()` deferToThread architecture exists to avoid).
The transport keeps the fixed 10-s cap (D1), so the callback latency is
bounded. Output: numbered list, one **verbatim** name per line (names clamped
to 256 code points for display), header line naming the kind with the server
base URL host only (never userinfo/credentials) + total count. Any `SDError`
prints the named `error: <code>` and no partial list (never falls back to
cached/prior values). The command performs **zero** state writes —
single-writer invariant intact (`@art options` is not in any queue lock
because it touches no record). Help/syntax/doc updates:
`docs/game/commands.md` row + anchor row in `command-reference.md`,
`tests/test_command_docs.py` green.

### D6 — Traceability timing and shard ownership

No `.github/evennia-shards.json` change: the ownership contract resolves
shard labels recursively, so new modules under `world/art/tests/` are already
owned by shard 4's `world.art` label (verified against
`tests.test_evennia_test_optimization_contract`'s exact-coverage assertion).
`covers_requirement` IDs for NEW-capability requirements are canonical only
after this change's deltas are synced into `openspec/specs/` at archive time
(the `env-overridable-settings` archive precedent): annotations are written
from the delta requirement slugs during implementation, and the
`tools.spec_traceability check` gate accepts them only after sync — the
sync + archive lands as one commit chain with the code. ID targets: new
capability requirement(s) on the enumeration/auth client tests; MODIFIED
`art-queue-worker` seed requirement on the settle test; MODIFIED
`art-staff-commands` requirement on `@art options` tests; MODIFIED
`settings-environment-overrides` inventory requirement stays on the existing
inventory tests (extended tables).

## Risks / Trade-offs

- [Forge-only `sd-modules`/dtype on a non-Forge server] → behavior documented;
  server-side error surfaces as `sd_http_error` at generation, exactly like
  any wrong-name typo; `@art options modules` on A1111 404s → named error,
  no list. Not worth client-side fork detection.
- [Deferred option-list arriving after a disconnect] → the reply is sent via
  the invoking caller's `msg`; a vanished session drops the message the same
  way any deferred command reply does. The command itself never blocks the
  reactor; worst-case latency is the fixed 10-s transport cap.
- [Password leakage] → header built from settings at request time; error
  paths stringify exception types/messages only (no headers); explicit tests:
  SDError messages and logs never contain the password literal; `.env.example`
  and the guide list both names as `secret_settings.py`-only with no example
  value.
- [`GeneratedImage` interface breaks existing seams] → the two fakes and all
  `client.generate` callers are repo-internal; updated atomically in this
  change; `test_sd_worker.py`/`test_worker.py` cover the boundary.
- [Seed parse strictness loses reproducible seeds on exotic servers] → strict
  only on type (non-negative int); missing/garbage → None, generation itself
  unaffected.
