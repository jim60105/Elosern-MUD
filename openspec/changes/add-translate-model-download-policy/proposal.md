# Add translate model download policy

## Why

The translation stage shipped its model acquisition as seed-only (design D2 of
`add-ctranslate2-translate-backend`): the server never fetches, and an unseeded
volume is a bounded `art_translate_unavailable`. The background-removal stage
already runs a better policy — `ART_REMBG_DOWNLOAD_ENABLED` (default `true`) lets
the library fetch its model on first use into the pinned persistent volume, and
`=false` turns deployment into a provably air-gapped configuration that verifies
the artifact before importing the library. Translation is the only art stage with
a model left out of that dual-track pattern, which makes the first Han-bearing
generation on a fresh deployment silently degrade forever unless an operator
happens to know about `scripts/fetch-translate-model.sh`. Aligning the two stages
removes a whole class of "the stage looked broken but was unseeded" deployments.

## What Changes

- New environment-backed boolean `ART_TRANSLATE_DOWNLOAD_ENABLED` (default
  `true`), joining the typed settings-environment-overrides inventory exactly
  like `ART_REMBG_DOWNLOAD_ENABLED`.
- `true` (default): the CTranslate2 backend MAY download and unpack the Argos Open
  Tech `translate-zh_en-1_9` package (`https://argos-net.com/v1/…`, a ~74 MB zip)
  at first use into the code-only `ART_TRANSLATE_MODEL_DIR` persistent volume,
  mirroring how rembg's library fetch is pinned to its volume. The fetch is lazy
  (never at import or boot), runs only under the construction lock in the
  worker-thread path, verifies the zip and its layout, keeps the CC-BY 4.0
  README, lands atomically, and every fetch/verify failure is a bounded
  `art_translate_unavailable` that degrades through the existing
  `art_translate_failed` warn — never a worker crash, never a settled `failed`.
- `false`: today's exact behavior becomes the supported air-gapped
  configuration — the pre-import layout check fails immediately with the bounded
  `art_translate_unavailable`, structurally no network. `scripts/fetch-translate-model.sh`
  stays as the operator seeding route for this mode (and for pre-seeding the
  volume before the first download-enabled run).
- **BREAKING (spec text only):** the `art-prompt-translation` requirement
  "The model artifact is operator-seeded and its absence is bounded" — which
  mandates "the backend SHALL NOT download, fetch, or otherwise populate that
  directory at run time" — is superseded by a dual-track acquisition requirement
  under a new name.
- The container contract keeps its teeth: the image STILL bakes no translation
  model; the layer-scan contract is unchanged. Only the sentence "this volume
  SHALL NOT be populated at run time" changes to match rembg's volume language.
- Fixes an adjacent known defect: `scripts/fetch-translate-model.sh` prints the
  unprefixed volume name `evennia-translate`, while podman-compose mounts the
  project-prefixed `mud_evennia-translate` — the printed busybox seed command
  silently seeds an orphan volume. The script resolves the real volume name
  dynamically (via `podman volume ls`) before printing it.

## Capabilities

### New Capabilities

None. This change re-policies the acquisition behavior of the existing
`art-prompt-translation` backend.

### Modified Capabilities

- `art-prompt-translation`: the seed-only model-artifact requirement is renamed
  and rewritten as the dual-track acquisition requirement (download-enabled
  first-use fetch into the volume, download-disabled air-gapped verification,
  bounded degradation for both), plus a new requirement that the operator
  seeding helper name the REAL compose volume.
- `settings-environment-overrides`: `ART_TRANSLATE_DOWNLOAD_ENABLED` joins the
  exact env-backed inventory (case-insensitive boolean words, default `true`)
  and the test-settings sanitization list; `ART_TRANSLATE_MODEL_DIR` stays
  code-only.
- `container-image`: the `/app/server/.translate` volume paragraph changes from
  "never populated at run time" to the rembg-parity contract — fetched on first
  use into the volume when downloads are enabled, operator-pre-seeded with
  `ART_TRANSLATE_DOWNLOAD_ENABLED=false` when air-gapped, never baked into an
  image layer.

## Dependencies

depends-on: add-ctranslate2-translate-backend (archived 2026-09-23 — landed:
`world/art/translate_ct2.py`, `ART_TRANSLATE_MODEL_DIR`, the seeder script, the
volume).

Independent of `recut-art-portrait-prompt` (archived) in both directions.

Size: ~24 tasks / one engineer-day.

## Batch:

Batch: solo.

depends-on: add-ctranslate2-translate-backend
depends-on: (none active; see conflict notes)

Code-conflict notes: owns `world/art/translate_ct2.py`,
`scripts/fetch-translate-model.sh`, and the translate-acquisition requirements. It
APPENDS lines to `server/conf/settings.py`, `server/conf/test_settings.py`,
`server/conf/tests/test_env_overrides/_support.py`, `.env.example`,
`docs/development/settings-and-environment.md`, and `world/art/tests/test_translate.py`
— files no active change (`implement-church-combat-ministry`,
`implement-church-order-catalogue`; their deltas touch only `church-ordination`
and `title-system`) reads or edits. Its `settings-environment-overrides` delta is
written against the post-ctranslate2 archived text, which is the current main spec.

## Impact

- Edited: `world/art/translate_ct2.py` (download track + air-gapped gating),
  `server/conf/settings.py`, `server/conf/test_settings.py`,
  `server/conf/tests/test_env_overrides/_support.py` (inventory/default/coercion/
  rejection rows), `world/art/tests/test_translate.py`, `.env.example`,
  `docs/development/settings-and-environment.md`, `scripts/fetch-translate-model.sh`
  (volume-name fix; download/verify logic otherwise unchanged).
- Unchanged by design: `compose.yaml`, `Containerfile`, the image layer-scan
  contract (no model baked), `ART_TRANSLATE_MODEL_DIR` code-only status, the
  translation seam's bounded codes and worker event contract, and the fake
  translator used by tests and the browser harness (no test ever downloads).
