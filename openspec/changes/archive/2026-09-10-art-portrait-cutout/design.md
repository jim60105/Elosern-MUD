## Context

`world/art/worker.py::_settle_one` is a four-step pipeline per claimed record:

```
client.generate(subject, description) -> GeneratedImage(PNG bytes + provenance)
formats.encode(...)                   -> configured store format + metadata policy
_write_temp(identity, encoded)        -> unique temp file inside the store directory
settle_generated / settle_gallery_generated -> atomic publish under the queue lock
```

Every failure between those steps already maps to a bounded named code and a terminal
`failed` settle that retains the record's prior valid output. The whole pipeline runs on
one background Twisted thread guarded by a single worker slot; the reactor thread never
blocks on it. Store-path confinement, atomic replace, gallery card append, and lease
reclaim are settled invariants with existing tests.

Background removal is a **local CPU post-process on the returned bytes**. It needs no new
concurrency model, no new persistence, no new store path, and no change to the sd-webui
wire protocol. The only genuinely new things are: a heavy optional dependency, a 1 GB
model artifact, an alpha channel that previous stages never had to think about, and two
more ways one job can fail.

Survey evidence this design is built on (measured on the project's own machine):

| Fact | Value |
| --- | --- |
| `rembg` + `bria-rmbg`, CPU only | works, quality excellent (hair edges, ground-shadow removal) |
| ONNX session build | ~3.1 s, one time per process |
| Inference, 920x1536, 24 cores | ~9.8 s |
| Model artifact | ~1.02 GB, fetched on first use |
| CUDA execution provider | not viable — host is missing `libcudnn.so.9`, `libcublasLt.so.12`, `libcufft`, `libcurand`, `libcudnn_ops`, `libcudnn_adv`; with pip `nvidia-*` wheels forced in, `bria-rmbg` OOMs beside sd-webui on the shared RTX 3060 12 GB |

## Goals / Non-Goals

**Goals:**

- Character and monster portraits — classic records **and** gallery cards — are stored
  with a transparent background.
- Scene art is byte-for-byte unchanged.
- CPU-only execution. The GPU stays entirely with sd-webui.
- A cutout failure is a bounded, diagnosable, recoverable per-job failure. It never
  blocks a drain, never re-issues an sd-webui generation, never corrupts or replaces a
  prior valid output, and never leaves a job `in_progress`.
- No test loads a real model, opens a socket, or takes seconds.
- The model is a configuration choice, not a hard-coded licence commitment.

**Non-Goals:**

- Re-cutting already stored portraits. There is no backfill command and no migration —
  the project has no released users, and `@art requeue` / `@art retry` already regenerate
  on demand.
- Cutting out **seed-synchronized** art. `world/art/gallery_seed.py` imports
  operator-supplied PNGs from the `art-seed` mount straight into the store; that path
  never touches the worker, so seeded portraits keep their backgrounds. A gallery can
  therefore legitimately hold a mix of cut-out generated cards and opaque seeded cards.
  This is a known, accepted inconsistency, not an oversight: the operator supplied those
  files deliberately and the engine must not silently rewrite operator input. An operator
  who wants uniform cutouts pre-processes the seed folder or deletes the seeded card and
  requeues.
- Per-subject-kind output formats. One `ART_SD_OUTPUT_FORMAT` continues to govern the
  whole store (D4).
- Recording the cutout in the embedded A1111 metadata (D11).
- GPU / CUDA execution providers, in any form (survey evidence above).
- Alpha-aware presentation work in the webclient. The panel keeps rendering whatever the
  media route serves; PNG/WebP/AVIF alpha is already handled by browsers.
- Trimming, auto-cropping, or re-centring the cut-out subject.

## Decisions

### D1 — The stage runs on the transport PNG bytes, before `encode`

`_settle_one` becomes `generate -> cutout -> encode -> write -> publish`. The cutout
backend takes PNG bytes and returns PNG bytes (RGBA), so `formats.encode`'s existing
contract — "the input must decode as a PNG container" — is satisfied unchanged, and the
sanitization, metadata, format-selection, and extension logic all stay in exactly one
place.

*Alternatives rejected.* (a) Cutout **after** `encode`: would have to decode the store
format, re-encode, and reapply the metadata policy — two lossy round-trips for
webp/avif and a duplicated metadata path. (b) A **second** stored file (opaque original
plus a cutout sibling): doubles store size, needs a second identity in the record, a
second media-route shape, presenter changes, and a second prune rule. The user's
requirement is that the stored portrait *is* the cutout, so the extra file has no
consumer. (c) Asking sd-webui for a transparent output (an extension such as
`rembg`/`ABG` inside Forge): puts a mandatory server-side extension into the wire
contract, moves the failure mode behind the network, and re-introduces the GPU VRAM
problem the survey ruled out.

### D2 — `ART_REMBG_ENABLED` defaults to **false**

The feature ships fully implemented, fully tested, and off, and an operator turns it on
with one line in `.env`.

Rationale, in order of weight:

1. `server/conf/test_settings.py` exists to guarantee that "the effective settings under
   test are exactly the documented code defaults" — it pops every env-backed name before
   importing production settings, and `test_env_overrides.py` enforces that list against
   the settings AST. A default-on stage would therefore make **every existing portrait
   worker test** in `world/art/tests/` and `commands/tests/` load onnxruntime and a 1 GB
   ONNX model, in CI, per test. Exempting the flag in `test_settings.py` would be a
   deliberate hole in a contract that exists precisely to stop such holes.
2. `AGENTS.md`: the deterministic game must remain fully playable with all image
   services offline. A default that fetches 1 GB on first use fails that standard for a
   fresh checkout, even though the failure is bounded.
3. The default is where a licence commitment would otherwise become implicit (see D9).
4. Cost of being wrong is one character in `settings.py`; cost of the opposite mistake is
   a CI suite that needs a model download.

`.env.example` and `docs/gm/prompts.md` carry the opt-in line with its cost stated
(~1 GB, ~10 s per portrait), so the feature is discoverable rather than hidden.

*Alternative rejected:* default-on in `compose.yaml` only (`${ART_REMBG_ENABLED:-true}`)
while the code default stays false. It delivers the feature to real deployments, but it
splits the effective default across two files, which is exactly the drift
`settings-environment-overrides` was written to prevent.

### D3 — Scope is an explicit subject-kind allowlist, applied to both publication paths

`world/art/cutout.py` owns `CUTOUT_SUBJECT_KINDS = frozenset({ArtSubjectKind.CHARACTER,
ArtSubjectKind.MONSTER})` and an `applies_to(kind)` predicate.

- **Allowlist, not `kind is not SCENE`.** A future fourth subject kind (an item icon, a
  location marker) must make a deliberate decision instead of silently inheriting a
  cutout. A contract test iterates `ArtSubjectKind` and asserts the allowlist decides
  every member, so adding a kind fails the suite until someone chooses.
- **Both paths, one gate.** `_settle_one` already computes `subject = subject_for(record)`
  for classic and gallery records alike (a gallery job record carries `kind` and
  `subject_key` exactly like a classic one), so the single predicate covers
  `portrait/character/…`, `portrait/monster/…`, and
  `gallery/<kind-dir>/<subject-key>/<image-id>…`. Gallery portraits are the same portrait
  art displayed in the same panels; excluding them would produce a gallery where the
  default card is cut out and the alternates are not.
- Scene subjects never reach the backend at all — not "call it and discard", but "no
  call". Byte-for-byte identical output is then structurally guaranteed, and a test
  asserts the fake backend recorded zero calls for a scene drain.

### D4 — JPEG + cutout is a fail-closed boot error, not a silent alpha drop

`formats.encode` normalizes RGBA to RGB for JPEG (`image.convert("RGB")`). `rembg`
returns the original RGB with an alpha mask applied, so `convert("RGB")` would discard
the mask and store **the original portrait, background and all**, indistinguishable from
a non-cutout run. That is the worst possible outcome: a silent lie.

So `server/conf/settings.py` raises `ImproperlyConfigured` when `ART_REMBG_ENABLED` is
true and the effective `ART_SD_OUTPUT_FORMAT` is `jpeg`, naming both settings and the
reason. The check runs **after** the `secret_settings` import, next to the derived
`ART_SD_OUTPUT_EXTENSION`, so every override path (environment, `secret_settings.py`) is
covered by the one check — the same placement rule the extension derivation already
follows.

`png`, `webp`, and `avif` all carry alpha through Pillow (the project pins
`pillow>=12.3.0`, whose bundled AVIF plugin encodes RGBA), and
`art-output-format-pipeline` gains an explicit alpha-preservation requirement so this is
tested rather than assumed.

*Alternative rejected:* forcing portrait outputs to `.png` while scenes keep the
configured format. It contradicts the standing "`ART_SD_OUTPUT_FORMAT` is the single
source of truth and no consumer re-derives the extension" requirement, and it would ripple
into `expected_output_identity`, `output_identity_for`, the extension-change deletion
ordering, the media route's closed extension set, the presenter, and the gallery prune —
far more than a day's work, for a configuration nobody has asked for.

### D5 — A cutout failure fails the job; it never degrades to the original image

Two new bounded codes, deliberately split so the log tells the operator which lever to
pull:

| Code | Meaning | Operator action |
| --- | --- | --- |
| `art_cutout_unavailable` | the backend or its model could not be made ready — bad `ART_REMBG_BACKEND` path, `rembg`/`onnxruntime` import failure, model absent with downloads disabled, session build/download failure | fix config, network, or model cache |
| `art_cutout_error` | the backend was ready and the removal itself failed — undecodable input, inference error, non-PNG result | inspect the image / the model |

Both settle through the paths that already exist: a classic record settles `failed` with
the code and keeps its prior valid output; a gallery job settles through
`settle_gallery_failed` (no card appended, code recorded on the subject's gallery record,
spent job record deleted). Batch-mates are unaffected. `@art retry` re-enqueues once the
cause is fixed.

*Alternative rejected — "degrade to storing the original".* The pipeline's entire ethos is
bounded named failures over silent substitution, and a stored opaque portrait is
indistinguishable from a stored cutout: the operator would find out from a user complaint,
not from `@art status`. Failing keeps the prior valid image on disk (better than replacing
a good cutout with a background-ful one) and makes the fault visible and retryable.

The sd-webui generation itself is *never* re-issued or failed by this stage. It has
already completed; the discarded work is one local pass, and no HTTP request is repeated.

### D6 — Lease bound: an additive allowance, charged only when the stage is enabled

Today: `per_item = ART_SD_TIMEOUT_SECONDS + _CONVERSION_ALLOWANCE_SECONDS (60)`,
`lease = ART_SCHEDULER_LIMIT * per_item + 5`.

New: `per_item = ART_SD_TIMEOUT_SECONDS + _CONVERSION_ALLOWANCE_SECONDS +
(ART_REMBG_ALLOWANCE_SECONDS if ART_REMBG_ENABLED else 0)`.

Default `ART_REMBG_ALLOWANCE_SECONDS = 120`, giving `600 + 60 + 120 = 780` per item and
`4 * 780 + 5 = 3125 s` for a default batch. Sizing: measured 3.1 s session build (once)
+ 9.8 s inference on 24 cores; a 4-core box scales roughly 6x to ~60 s, so 120 s is about
2x headroom on the slowest plausible target. Charging zero when the stage is disabled
keeps every existing lease assertion and today's default behavior exactly as-is.

**The one-time model download is deliberately not inside this bound.** A 1 GB fetch on a
slow link can exceed any sane lease, and the download runs inside a third-party library
we cannot preempt from another thread. The existing claim-token invariant already makes an
overrun safe rather than corrupting: if the lease expires mid-flight the record is
reclaimed to `pending`, the worker's later `settle_*` call sees a stale generation token,
returns `None`, and `_settle_one` returns `None` — nothing is published, nothing is
double-settled, and the reclaimed record simply runs again with the model now cached. The
only cost is one wasted generation. `ART_REMBG_DOWNLOAD_ENABLED=false` (D10) turns this
window off entirely for deployments that pre-seed the cache.

*Alternative rejected:* a hard wall-clock timeout enforced by a watchdog thread. ONNX
Runtime inference is not interruptible from Python; the watchdog could report but not
stop, so it would add a thread and a lie. The setting is therefore named
`ART_REMBG_ALLOWANCE_SECONDS`, not `..._TIMEOUT_SECONDS` — it is a lease budget, and its
name does not promise enforcement that does not exist.

### D7 — The backend is an injectable seam with a process-cached session

`world/art/cutout.py`:

- `CutoutError(Exception)` with a `.code`, mirroring `SDError`.
- `remove_background(png_bytes: bytes) -> bytes` — the module-level entry point
  `_settle_one` calls. It resolves the configured backend, delegates, and maps *every*
  escaping exception to one of the two bounded codes. Nothing unbounded reaches the
  worker; the worker's generic `except Exception -> sd_internal_error` arm stays a
  backstop, not the normal path. It also **validates the backend's return value** —
  non-`bytes`, empty, or missing the PNG magic raises `art_cutout_error`. Without that
  8-byte check the bad value would flow into `encode`, whose `_decode_transport_png`
  would reject it as `sd_format_error`: a bounded code, but one that blames the wrong
  stage and would send an operator to the format settings for a backend fault.
  The validation is NOT only the 8-byte magic check: the seam also requires the value
  to decode as a PNG whose mode carries an alpha channel (`RGBA`/`LA`/`PA`). That is
  the postcondition of the stage's own contract ("returns PNG bytes carrying an alpha
  channel"): a backend that returns the original opaque portrait — the exact
  silent-degradation outcome D5 forbids — or corrupt magic-prefixed bytes must fail
  the job as `art_cutout_error` before `encode` is ever reached. The check is
  decode-only: the validated bytes are forwarded to `encode` untouched (no re-encode).
- `resolve_cutout_backend()` — imports the `ART_REMBG_BACKEND` dotted path, exactly like
  `resolve_sd_client()`. Resolution failure is `art_cutout_unavailable`.
- `RembgCutoutBackend` — the real implementation. `rembg` and `onnxruntime` are imported
  **lazily inside the first call**, never at module import, so `world/art/cutout.py`
  stays importable (and the settings module stays loadable) on a checkout where the
  optional stack is broken. It builds one `rembg` session per `(model name)` in a
  module-level cache; the lock guards **session construction only** (check, lock,
  re-check), never the inference call, so a future second worker slot would not serialize
  on a 10 s pass. It pins `providers=["CPUExecutionProvider"]` — belt and braces, since
  the CPU-only `onnxruntime` wheel exposes no other provider anyway — and applies the
  `ART_REMBG_THREADS` cap through whatever mechanism the locked `rembg` version supports.
  **That mechanism is version-dependent and must be pinned, not assumed:**
  `rembg.new_session()` in the 2.x line constructs its own `ort.SessionOptions`
  internally and reads `OMP_NUM_THREADS` from the environment, so a caller-supplied
  `SessionOptions` may not be reachable through that entry point. Task 3.6 checks the
  locked version and implements whichever of the two paths it offers; the spec is written
  against the observable outcome (the cap reaches the session's thread configuration)
  rather than a particular call signature.
- `world/art/fake_cutout.py::FakeCutoutBackend` — deterministic double, mirroring
  `FakeSDWebUIClient`: records every call, replays scripted `CutoutError`s
  (`fail_every_call` / `add_failure`), and otherwise returns a real PNG whose alpha
  channel has been zeroed over a fixed region, so an alpha assertion in a test is a real
  assertion and not a tautology. No import of `rembg`, no file access, no network.

**The double alone does not make the alpha assertions meaningful.**
`world/art/fake_sd_client.py::DEFAULT_PNG` is a 1x1 *already transparent* PNG, so a
worker-level assertion that "the stored portrait has transparent pixels" would pass even
with the stage disabled or with a passthrough backend — a tautology dressed as a test.
Every worker integration test for this change therefore drives the sd fake with an
**opaque, multi-pixel** fixture and asserts both that the fake backend recorded the call
and that the stored bytes differ from the same job's disabled-stage output. See task 6.3.

Resolution happens per record inside `remove_background`, not once per batch like the sd
client. That is deliberate: a broken `ART_REMBG_BACKEND` then fails only the portrait
records, while scene batch-mates in the same drain still succeed. `importlib` caches the
module and the session cache is module-level, so per-record resolution costs an attribute
lookup.

*Alternative rejected:* calling `rembg` directly from `worker.py`. It would put a
network-and-1-GB-model dependency inside the module every art test imports, with no way
for a test to substitute it — the exact problem `ART_SD_CLIENT` was introduced to solve.

### D8 — The model cache is a code-only path on its own persistent volume

`ART_REMBG_MODEL_DIR = os.path.join(GAME_DIR, "server", ".rembg")`, mounted as a named
volume at `/app/server/.rembg`.

- **Why not the default `~/.rembg/models`.** The image sets `HOME=/tmp` and compose
  mounts `/tmp` as `tmpfs`. The default location would therefore re-download 1 GB on
  every container start.
- **Why not inside `ART_STORE_ROOT`.** The store root is governed by
  `_resolved_under_root` confinement, the media route's closed extension set, and the
  gallery orphan prune. Parking a 1 GB `.onnx` file inside it means every one of those
  invariants acquires a new exception to reason about. A sibling directory costs one
  `install -d` line and one volume, and keeps the store root exactly what its spec says
  it is.
- **Why code-only (no environment override).** Identical to the standing
  `ART_STORE_ROOT` rationale in `settings-environment-overrides`: a mistyped value
  silently relocates a large artifact off the persistent volume. `secret_settings.py`
  remains the escape hatch for a nonstandard layout.
- **How `rembg` is pointed at it.** The backend sets the model-home environment
  variables `rembg` reads (`U2NET_HOME` and `REMBG_HOME` — both, so the behaviour does
  not depend on which naming the pinned version uses) to `ART_REMBG_MODEL_DIR`
  immediately before the lazy `rembg` import and session build, and creates the directory
  if absent. Task 3.4 pins the exact name against the locked `rembg` version and the unit
  test asserts our backend set both names from the setting.

### D9 — `ART_REMBG_MODEL` is a closed choice set, default `bria-rmbg`

Accepted set: `bria-rmbg`, `isnet-anime`, `isnet-general-use`, `u2net`, `u2netp`.

- **Closed, not free text.** An unknown name would otherwise reach `rembg`'s session
  factory and fail *every portrait job at runtime*; a closed set fails at boot with the
  variable, the value, and the accepted list — the fail-closed rule the whole `ART_*`
  family already follows.
- **Why the choice exists at all.** `bria-rmbg` wraps BRIA's RMBG-2.0 weights, which are
  BRIA-licensed: free for non-commercial use, commercial use needs a BRIA licence. The
  setting makes the permissively licensed `isnet-anime` (~176 MB) a one-variable swap
  followed by `@art requeue`, with no code change. The operator owns the licence
  decision; the settings comment and the docs table say so explicitly, in both
  `docs/gm/prompts.md` and `docs/development/settings-and-environment.md`.
- The default is `bria-rmbg` at the project owner's explicit request, and D2's
  default-off means no licence obligation is incurred by merely merging this change.

### D10 — `ART_REMBG_DOWNLOAD_ENABLED` (default true) bounds the first-use fetch

When false, the backend checks for the model artifact under `ART_REMBG_MODEL_DIR` before
building a session and raises `art_cutout_unavailable` immediately if it is absent — no
`rembg` import, no network call, no unbounded wait. This is what makes "the model is
unavailable" a *bounded* failure rather than a hang, and it is the supported air-gapped
configuration (pre-seed the volume, disable downloads).

When true, `rembg`'s own first-use download runs inside the session build, under the
module lock, on the worker thread. D6 covers the lease consequences, and D6a closes the
stale-failure hole that an unbounded wait opens.

### D11 — Embedded generation metadata is unchanged

`formats.encode` keeps emitting exactly today's A1111 parameters block, assembled from
the `GeneratedImage` provenance. No cutout marker is added.

Reasoning: the parameters block describes the *generation* — the request sd-webui
actually served — and that description remains true. Adding a field would break the
A1111 reader compatibility the format spec is built around and would put a new string
inside the "provably metadata-free when the flag is off" scenarios. The cutout is
recorded where post-processing belongs: the boundary event (D12), which carries the model
name.

### D12 — Two boundary events, through the facade

- `art_cutout_done` (info) — `{job, subject, image_id, model, duration_ms}`.
- `art_cutout_failed` (warn, with `exc=`) — `{job, subject, image_id, model, code}`.

`image_id` is the empty string for a classic record and the gallery image id for a
gallery job, matching how `_settle_one` already carries it. Both are emitted from
`world/art/worker.py` with named facade imports, so tests patch the caller module's
binding per the observability rules. `world/art/cutout.py` raises and does not log, so
there is exactly one event per outcome and no double reporting.
`tools/observability_freeze.json` is empty and stays empty — the new module is a facade
adopter from birth.

The events report the **stage** outcome, not the job outcome: a job whose cutout
succeeded and whose later `encode` or publish failed logs `art_cutout_done` followed by
the existing `sd_generation_error` / `sd_job_settled` pair. That is the correct reading —
the two events answer different questions — and the docstring says so, so nobody later
"fixes" it into a job-level event.

The two new codes need no consumer change: `last_error_code` is a free-text
`AttributeProperty` on both the asset record and the `GalleryRecord`, rendered verbatim
by `commands/art.py`, and no presenter or wire payload validates it against a closed set.
`worker_output_out_of_root` is the existing non-`sd_`-prefixed precedent.

### D6a — Classic terminal-failure settles become claim-token guarded

Today's classic failure path is guarded by STATUS ONLY: `_run_and_settle_batch` calls
`queue.settle(...)`, and `queue._settle_by_key` checks nothing but
`status == IN_PROGRESS` — unlike `settle_generated` and `settle_gallery_failed`, which
both reject a stale `generation_token`. Every failure path pre-dating this change sits
well inside the lease, so the gap is unreachable today. This change deliberately
introduces the first over-lease-possible step (the one-time model download, D6): if the
lease expires mid-download, the record is reclaimed to `pending` and re-claimed with a
new token, and the old worker's eventual `art_cutout_unavailable` settle would then mark
the NEW claim `failed` — stealing a live job's state from an obsolete attempt.

Fix: `queue.settle` and `queue._settle_by_key` gain a required `generation_token`
argument, and the worker passes the claim-time token it already snapshots before any
blocking work. The snapshot is captured ONCE per claim and threaded through the whole
worker path: `_settle_one` receives it as an explicit argument and NEVER re-reads
`record.db.generation_token` (that attribute is live storage — a record reclaimed and
re-claimed between the batch snapshot and a later record's settle would hand the old
worker the NEW claim's token). The same snapshot feeds `settle_generated`,
`settle_gallery_generated`, `settle_gallery_failed`, and the classic terminal `settle`.
A mismatch is a no-op returning `None`, exactly like the publish-side
rule: the stale failure publishes nothing and settles nothing, and the current claim
finishes on its own terms. `_fail_batch` (the batch-level `sd_client_config_error`
path) is likewise re-checked under the same token discipline — its failure occurs
before any blocking call, so it never goes stale in practice, but the guard is applied
uniformly rather than by an argument about timing. The gallery-failed path already
guards and is unchanged.

*Alternative rejected:* bounding or cancelling the download from our side. ONNX/urllib3
fetches are not interruptible from another thread, and any wall-clock we enforce
ourselves would either be too short for a real first fetch or long enough to make D6's
lease arithmetic moot. The token guard is the same invariant the publish side already
trusts, made symmetric.

## Risks / Trade-offs

- **Silent alpha loss through a lossy encoder** → D4 refuses JPEG at boot, and
  `art-output-format-pipeline` gains an explicit alpha round-trip requirement covering
  `png`, `webp`, and `avif` so the encoder path is asserted, not assumed.
- **CI or a fresh checkout accidentally pulling a 1 GB model** → default-off (D2), an
  injectable fake used by every test (D7), and the fake is what `world/art/tests/`
  installs through `override_settings(ART_REMBG_BACKEND=…)`.
- **ONNX saturating the box and hurting game latency** → the pass runs on the existing
  worker thread with the reactor free, and `ART_REMBG_THREADS` caps the session's
  thread count for operators who share the box with sd-webui. Default `0` keeps ONNX
  Runtime's own choice.
- **Resident memory in the game server process.** The session cache is deliberately
  process-lifetime, so after the first portrait the Evennia server's RSS grows by roughly
  the model size plus ONNX arenas — on the order of 1–1.5 GB for `bria-rmbg` — and never
  shrinks. On a small VPS this is the difference between running and being OOM-killed.
  Mitigations, in order: the stage is off by default and pays nothing until enabled;
  `isnet-anime` (~176 MB) costs an order of magnitude less; and the ops documentation
  states the figure so it is sized for, not discovered. A TTL-based session eviction was
  considered and rejected for this change — it buys back memory only between generation
  bursts, at the price of a timer thread and a repeated ~3 s rebuild, and it can be added
  later without touching this seam.
- **Supply chain: a ~1 GB binary fetched at runtime and executed as an ONNX graph.** The
  engine introduces no download URL of its own — the fetch is `rembg`'s, from its own
  pinned release location with its own integrity check, and `rembg`/`onnxruntime` are
  themselves pinned in `uv.lock`. The hardened configuration is to pre-seed the volume
  from a trusted machine and set `ART_REMBG_DOWNLOAD_ENABLED=false`, which makes runtime
  network access for this feature structurally impossible; that is why the knob exists
  and not only for air-gapped hosts.
- **First-use download overrunning the lease** → safe by the existing claim-token
  invariant (D6): worst case is one wasted generation and an automatic re-run, never a
  double publish or a corrupted output. `ART_REMBG_DOWNLOAD_ENABLED=false` removes the
  window for deployments that pre-seed the cache.
- **Dependency weight and Python 3.13 / Pillow 12 compatibility** → `uv add` resolves
  against the pinned interpreter and `pillow>=12.3.0`; if `rembg` pins an incompatible
  Pillow the lock resolution fails loudly at task 1.1, before any code is written. That
  is the earliest possible failure point and it costs nothing to discover.
- **BRIA licence exposure** → D9 (closed-set model knob with a permissive alternative)
  plus D2 (off by default) plus explicit documentation. Engineering cannot resolve a
  licensing question, only keep it visible and cheap to act on.
- **Cut-out quality on an unusual portrait** (a subject blending into the background,
  a heavily stylized render) → out of scope to fix here; the operator's levers are
  `ART_REMBG_MODEL` and `@art requeue`, and the original opaque render is one requeue
  away with the flag off.

## Migration Plan

None required — the project has no released users and this change adds no persisted
field, no schema change, and no data transformation. Existing stored portraits keep
their backgrounds until someone requeues them; enabling the flag affects only art
generated after the restart. Rollback is `ART_REMBG_ENABLED=false` plus a restart, with
no store cleanup needed.

## Open Questions

- Should a follow-up add a staff-facing bulk re-cut (`@art requeue --all-portraits`)?
  Deliberately out of scope here; the per-subject requeue path already exists and a bulk
  operation is a separate decision about queue pressure.
- The exact `rembg` model-home environment variable name is version-dependent; this
  design sets both known names (D8) rather than guessing, and task 3.4 pins it against
  the locked version.
