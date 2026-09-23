# Design — translate model download policy

## Context

`world/art/translate_ct2.py` today: `translate()` runs `_check_layout(model_dir)`
(missing/unreadable components → bounded `art_translate_unavailable`, no library
import, no network), then `_engine()` → `_build_engine()` under `_ENGINE_LOCK`
(lazy imports of `ctranslate2`/`sentencepiece`, CPU-pinned translator). The fetch
route lives only in `scripts/fetch-translate-model.sh`, a host-side bash script
using `curl` + `unzip`. `world/art/cutout.py` shows the target shape:
`ART_REMBG_DOWNLOAD_ENABLED=false` verifies the artifact under
`ART_REMBG_MODEL_DIR` BEFORE importing rembg and fails immediately; `=true`
(letting the library fetch on first use) is the default, pinned to the volume via
`U2NET_HOME`/`REMBG_HOME`.

Constraints: ctranslate2 offers no model-download mechanism of its own (unlike
rembg), so the fetch must be ours. The seam's contract is unchanged: the stage
raises bounded codes, the worker logs `art_translate_failed` and degrades to the
authored description — a fetch failure therefore already has a safe degradation
path that never costs the image. The container image bakes no model and must
continue not to. The translation model is the Argos Open Tech
`translate-zh_en-1_9.argosmodel` zip (~74 MB; observed content-length
74,481,402), serving the `translate-zh_en-1_9/` package directory.

## Goals / Non-Goals

**Goals:**

- One knob, two tracks, exactly like rembg: default-on first-use fetch into the
  pinned volume; explicit-off air-gapped verification with structural no-network.
- Every download/verify/unpack surprise is a bounded `art_translate_unavailable`
  observed through the existing worker warn event; the worker never crashes.
- The operator seeding script stays, and prints a command that actually seeds the
  volume compose created.

**Non-Goals:**

- No model updating/versioning beyond first fill (a complete layout is NEVER
  re-fetched or upgraded; re-seeding remains `--force` script territory).
- No change to rembg, the seam's codes/events, `ART_TRANSLATE_MODEL_DIR`
  code-only status, the fake translator, or the image layer-scan contract.
- No new runtime dependency (the downloader is stdlib-only).

## Decisions

### D1 — The fetch lives in `translate_ct2.py`, stdlib-only, gated by the setting

ctranslate2 has no fetch to delegate to, so the backend module itself downloads
with `urllib.request` and unpacks with `zipfile` — the same verification rules the
bash script enforces: zip integrity, every member path inside
`translate-zh_en-1_9/` with no absolute or `..` segments, the five required
entries (`model/config.json`, `model/model.bin`,
`model/shared_vocabulary.json`, `sentencepiece.model`, `README.md`), and unpacking
exactly those (never `stanza/`). Alternative considered: import/copy the script's
logic as a shared Python module — rejected, the script is a host tool (curl,
podman) and the container has neither guarantee; ~80 lines of mirrored stdlib
checks is the honest duplication, pinned by a shared constant list of required
entries where the module can import nothing host-side.

### D2 — Fetch happens only when the layout check fails, inside the construction lock

Order inside the first engine miss: `_check_layout` → complete layout: today's
path unchanged, zero network. Incomplete/missing AND
`ART_TRANSLATE_DOWNLOAD_ENABLED=true`: fetch + verify + unpack, then re-check
layout, then the existing lazy-import engine build. AND `false`: today's exact
error, raised before any library import — structurally no network, because the
fetch call site simply does not exist in that branch. This keeps the "no import
cost for an unseeded deployment" property on the air-gapped track and adds
network only where the artifact is actually absent. Alternatives: fetch eagerly
at startup (rejected — boot-time network for a stage that defaults off and may
translate nothing); fetch on every process start (rejected — a complete layout is
never refreshed, matching rembg's fill-once volume semantics).

### D3 — File-level atomic landing; never destroy a valid seed

Each unpacked piece is written to a temp file in `ART_TRANSLATE_MODEL_DIR` and
`os.replace`d onto its final name, so every required file is atomically either
absent or complete; an interrupted fetch leaves a directory that still fails the
layout check and is repaired by the next attempt. The backend never deletes
existing content except by replacing exactly the required filenames, so a
valid seed is never in flight while being destroyed (the script's `replacement/`
concern does not apply: we fetch only when the layout is already invalid).
Concurrent-process races on one volume are benign by the same property. The
engine cache already serialises construction per process via `_ENGINE_LOCK`.

### D4 — Bounded fetch: size cap, timeouts, and a per-process failure latch

`urllib.request` with a connect/read timeout, a hard response-size cap of
128 MiB (generous headroom over the observed 74 MB), HTTPS URL fixed to
`https://argos-net.com/v1/translate-zh_en-1_9.argosmodel`, zero retries. Any
failure raises `art_translate_unavailable` AND trips a module-level latch: once a
download has failed in this process, later calls skip the fetch and fail
immediately, so an unreachable network cannot make every Han-bearing job re-bill
a 74 MB attempt. Recovery is a restart or an operator seed — acceptable because
the degradation costs a worse prompt, never an image. Alternative: timed backoff
retry — rejected until there is evidence the restart path is not enough; rembg
has no latch because its library retries invisibly, which is the behavior this
design deliberately avoids.
Observability: exactly one `art_translate_model_download_done` info event on
successful fetch (context: url, bytes, duration) and one
`art_translate_model_download_failed` warn event on the first failure (context:
url, bounded reason, exception chain), emitted from the backend module — the
download is a backend lifecycle event, not a stage outcome, so the seam's
"one boundary event per stage outcome" count is untouched and the failing job
still gets its normal `art_translate_failed` warn.

### D5 — No checksum pinning; trust model identical to rembg's fetch

The upstream publishes no digests, so the fetch trusts the HTTPS origin,
verifies zip integrity and layout, and keeps `README.md` (provenance, CC-BY 4.0
licence). This is the same trust posture as `ART_REMBG_DOWNLOAD_ENABLED=true`
fetching ONNX weights from GitHub releases; the air-gapped track with the script
remains the route for operators who refuse TOFU-over-HTTPS. Alternative
considered: pin the observed MD5 etag — rejected as a false pin (upstream may
re-issue the file; the layer-scan/layout checks carry the real guarantees).

### D6 — The knob follows `ART_REMBG_DOWNLOAD_ENABLED` in every surface

`ART_TRANSLATE_DOWNLOAD_ENABLED = _env_bool("ART_TRANSLATE_DOWNLOAD_ENABLED",
True)` in `settings.py` next to the other translate knobs; added to
`test_settings.py`'s pop list, the `_support.py` inventory/default/coercion/
rejection tables, the `.env.example` translate block (commented, mirroring the
rembg download-stanza wording), and the settings guide table. It is a plain
boolean knob — it does NOT touch `ART_TRANSLATE_MODEL_DIR`'s code-only rule.

### D7 — The script resolves the real compose volume name before printing it

`podman compose` prefixing makes the actual volume `mud_evennia-translate` (the
project name defaults to the directory name; `COMPOSE_PROJECT_NAME` changes it),
while the script currently prints `evennia-translate` — the printed busybox
command seeds an orphan volume and the operator's server keeps reading the empty
mounted one. Fix: at print time, when `podman` exists, resolve candidates in
order — exact `evennia-translate`, then `${COMPOSE_PROJECT_NAME:-mud}_evennia-translate`,
then a suffix scan of `podman volume ls --format '{{.Name}}'` for
`(^|_)evennia-translate$` — and print the first hit; when `podman` is absent or
no volume matches, print the project-prefixed default with an explicit note that
the name is unresolved. Detection of an existing volume is the same probe
already used by operators; the script gains no new failure mode (resolution
failure falls back to the annotated default, exit status unchanged).

## Risks / Trade-offs

- [First Han-bearing generation pays a ~74 MB download inside the worker]
  → bounded (size cap + timeouts, no retries), one-time per volume, and the job
  degrades gracefully if it fails or is slow; deployments that cannot tolerate it
  set the knob false and pre-seed.
- [The latch turns a transient network failure into a process-lifetime
  unavailability] → documented cost; the image still gets made, `ART_TRANSLATE_*`
  restarts are cheap, and the warn event tells the operator exactly why.
- [TOFU-over-HTTPS fetch without digest pinning] → identical posture to the
  shipped rembg default; air-gapped track + script remain for stricter operators.
- [Two containers racing the same fresh volume] → D3's per-file atomic replace
  makes every required file absent-or-complete for each writer; last writer's
  pieces are byte-identical content from the same URL.
- [Spec text churn: the seed-only requirement is renamed] → the delta uses
  RENAMED + MODIFIED so archived-change history stays readable.

## Migration Plan

No data migration: existing seeded volumes already satisfy the layout check, so
the new default never fetches over them. Rollback = set
`ART_TRANSLATE_DOWNLOAD_ENABLED=false` (immediately restores air-gapped
semantics) or revert the change (the volume contents are plain files the old code
already reads).
