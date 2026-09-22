## Why

The deterministic subject description that reaches sd-webui is Traditional
Chinese, because every source it is composed from is: the scene-archetype
registry, the bestiary tier text, the subrace label, the item registry's
`summary_zh`, the persona `appearance` block the player authored at character
creation, and the gallery panel's free-text box. The generation model is
prompted in English. Today those two facts simply do not meet, and the
image-generating half of the pipeline is reading a language it was not
prompted in.

The two largest sources — the persona `appearance` block and the gallery
`custom_prompt` — are authored by the player at runtime, so no amount of
compile-time bilingual data can cover them. A translation step immediately
before the request is the only placement that can.

It also cannot be a chat LLM. This is an adult game; an instruction-tuned model
with safety alignment will refuse some fraction of these descriptions outright,
and a refusal string is a far worse prompt than the untranslated Chinese. The
engine has to be a plain sequence-to-sequence machine translator, which has no
refusal behaviour to exhibit.

This change ships everything around that engine — the gate, the boundary, the
failure contract, the wiring, the fakes — so that
`add-ctranslate2-translate-backend` only has to drop the engine in.

## What Changes

- New `world/art/translate.py`: a bounded, injectable translation stage with
  the same shape as `world/art/cutout.py`. It raises named `TranslateError`
  codes and carries no logging; the worker owns every boundary event.
- New `ART_TRANSLATE_ENABLED` environment-backed setting (default `false`),
  plus the code-only `ART_TRANSLATE_BACKEND` dotted path (import-executing
  seam, same rationale that keeps `ART_SD_CLIENT` and `ART_REMBG_BACKEND` off
  the environment). No lease-allowance knob: the stage is sub-second next to a
  600-second per-item generation budget, and a one-off cold model load is
  covered by the claim-token rule exactly as the background-removal model
  download already is (design D6).
- A **language gate** that decides per line whether a line needs translating at
  all: a line carrying no Han character is already Latin-script and is passed
  through untouched, never sent to the backend. A player who types English tags
  into the gallery box gets them back byte-identical.
- Worker wiring in `world/art/worker.py::_settle_one`, between reading
  `source_description` and calling `client.generate(...)` — the same slot the
  cutout stage occupies on the other side of the call.
- **Failure is non-fatal, unlike the cutout stage.** Every translation failure
  falls back to the original description and the job generates and settles
  normally. A degraded prompt is worth an image; it is not worth losing one.
- Two worker-owned observability events, `art_translate_done` and
  `art_translate_failed`, and nothing at all for a skipped or
  nothing-to-translate subject.
- One `startup_step`-family boot line reporting which optional art stages are
  active, so an operator can see at a glance that a stage they believe is on is
  actually off. (The cutout stage shipped opt-in and its being silently
  disabled went unnoticed for weeks — one boot line makes that unrepeatable.)
- `world/art/fake_translate.py::FakeTranslator` for tests and the browser
  harness, which must never import a translation library.
- `.env.example`, `docs/development/settings-and-environment.md`, and
  `docs/gm/prompts.md` entries for the new environment knob.

The default `ART_TRANSLATE_BACKEND` names the class
`add-ctranslate2-translate-backend` creates. Until that change lands, an operator who
sets `ART_TRANSLATE_ENABLED=true` gets the bounded `art_translate_unavailable`
path and the untranslated description — which is exactly today's behaviour plus
one warn line. That is a deliberate forward-declared seam, not a stub.

## Capabilities

### New Capabilities
- `art-prompt-translation`: the prompt-translation stage — its position in the
  worker pipeline, the per-line language gate, the injectable backend contract
  and its output validation, the non-fatal failure semantics, and the
  observability events.

### Modified Capabilities
- `settings-environment-overrides`: `ART_TRANSLATE_ENABLED` joins the
  environment-backed inventory with its type and default, and
  `ART_TRANSLATE_BACKEND` joins the code-only import-executing-seam list.


## Dependencies

depends-on: (none)

Independent of `recut-art-portrait-prompt`: this change translates whatever
description it is handed and never reads the composition rules. Running the two
in either order, or together, produces the same end state.

Size: 43 tasks / one engineer-day.

## Batch:

Batch 1, in parallel with `recut-art-portrait-prompt`.

Code-conflict notes: owns `world/art/translate.py`, `world/art/fake_translate.py`,
`world/art/tests/test_translate.py`, the `_settle_one` stage call in
`world/art/worker.py`, the `ART_TRANSLATE_*` settings block, and the optional-stage
boot report in `server/conf/at_server_startstop.py`. It shares
`server/conf/tests/test_env_overrides/`, `.env.example`, and
`docs/development/settings-and-environment.md` with
`add-ctranslate2-translate-backend`, which queues behind it and appends to the same
inventories. Its `settings-environment-overrides` delta and that change's delta
edit the same two requirements, so the second one implemented rebases onto the
first — this is why they are sequential rather than parallel.

## Impact

- New: `world/art/translate.py`, `world/art/fake_translate.py`,
  `world/art/tests/test_translate.py`.
- Edited: `server/conf/settings.py` (two settings),
  `server/conf/test_settings.py` (`_ENV_OVERRIDES`),
  `server/conf/at_server_startstop.py` (the optional-stage boot report),
  `world/art/worker.py` (`_settle_one` stage call and two events; the lease
  bound is deliberately untouched), `web/tests/browser/browser_settings.py`,
  `server/conf/tests/test_env_overrides/` inventory literals,
  `world/art/tests/test_worker/test_translate_stage.py`,
  `world/art/tests/test_art_observability.py`,
  `.env.example`, `docs/development/settings-and-environment.md`,
  `docs/gm/prompts.md`.
- No new dependency. No network. No container change — this change introduces
  no model artifact and therefore no volume.
- Blocks `add-ctranslate2-translate-backend`, which supplies the backend class this
  change's default setting already names.
