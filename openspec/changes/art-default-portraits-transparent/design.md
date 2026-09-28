## Context

`world/art/fallback_keys.py` fixes the closed six-key vocabulary, the `.webp` extension, the 400 KiB bound, and the directory `web/static/art/defaults/`. The current images are 920×1536 RGB WebP painted on a light backdrop. `gallery_fallback.py` pairs each key with a face rectangle authored against those pixels. The `/art/defaults/` route serves them, and `ClosedVocabularyContractTests` pins directory and vocabulary to each other.

The runtime portrait pipeline already does exactly what the defaults need: `world/art/worker.py::_settle_one` runs `SDWebUIClient.generate(subject, description)` (which composes `art.portrait_prompt`/`art.negative_prompt` from `prompts/art.yaml` and renders on the `ART_SD_PORTRAIT_WIDTH`×`ART_SD_PORTRAIT_HEIGHT` canvas, 768×1024 by default, PNG transport) → `world.art.cutout.remove_background(png_bytes)` (alpha-PNG-validated, backend behind the `ART_REMBG_BACKEND` seam) → `world.art.formats.encode(..., output_format="webp")` (RGBA-preserving). The defaults simply predate the pipeline and were hand-authored opaque images.

## Goals / Non-Goals

**Goals:**
- Each committed default is regenerated from the project prompt library and carries an alpha channel whose background is fully transparent and whose figure is opaque, produced by the same generate → cutout → encode seams the runtime worker uses.
- File names, extension, and the closed key vocabulary are unchanged, so the route, resolver, and vocabulary contract keep working untouched.

**Non-Goals:**
- A runtime or on-the-fly cutout of the defaults.
- Changing the vocabulary, the route, the resolver, `world/art/cutout.py`, `world/art/sd_worker.py`, or `world/art/formats.py`.
- Queueing the defaults through the art job queue: they are committed static assets, produced by a one-shot tool, not per-install generation.

## Decisions

### D1. A one-shot tool over the existing seams, not a bespoke pipeline

`tools/regenerate_default_art.py` bootstraps Django (`DJANGO_SETTINGS_MODULE=server.conf.settings`, `django.setup()`, the pattern `tools/test_data_lint.py` already uses) and then calls, per key, exactly the runtime chain: resolve the SD client (`resolve_sd_client()`), `generate(subject, description)`, `cutout.remove_background(image.data)`, `formats.encode(png, ..., output_format="webp")` with the configured quality knobs. It writes the WebP into `web/static/art/defaults/<key>.webp` only when the decoded result carries alpha and stays under `FALLBACK_MAX_FILE_BYTES`; `--key <key>` regenerates a single file. It is run by hand and its output is committed; nothing in the game imports it.

Alternatives considered:
- Calling `rembg` directly with a hand-pinned session (the earlier draft of this change): duplicates the backend seam, bypasses the alpha validation in `remove_background`, and desynchronizes from whatever `ART_REMBG_BACKEND`/model the project standardizes on.
- Queueing six art jobs through `world/art/queue.py`: the queue settles into `settings.ART_STORE_ROOT` (the mutable media store), not `web/static/`, and would entangle committed assets with runtime job state.

### D2. Authored per-key description sentences

`art.character_description` / `art.monster_description` slots are entity-driven, and the six static keys have no entity. The tool therefore carries one authored, deterministic description sentence per key (e.g. an adult human man in travel-worn clothes; the hooded anonymous monster), rendered through `art.portrait_prompt` exactly as a real subject's description would be. Sentences live in the tool module, in English, following the existing prompt-library convention; they carry no player-facing prose.

### D3. The permissive cutout model for committed output

`ART_REMBG_MODEL` defaults to `bria-rmbg`, whose weights are BRIA-licensed (non-commercial). The committed images must not depend on that licence, so the tool pins `isnet-anime` at the call site using `override_settings`, independently of ambient configuration. Only explicit `--allow-bria` selects the ambient configured model instead; this escape hatch is not used for committed defaults. Before generation, the tool checks both backend-supported model-cache layouts. Missing weights require both `--allow-download` and enabled `ART_REMBG_DOWNLOAD_ENABLED`; otherwise it refuses before contacting sd-webui. The runtime stage keeps its own configurable default.

### D4. The contract test samples fixed regions, not a mask

The test decodes each file with Pillow and asserts:
- the mode carries alpha (`RGBA`),
- every pixel in the four 24×24 corner squares has alpha 0 (the prompt demands a flat backdrop and head-to-feet framing, so corners are backdrop),
- the mean alpha of the centre column band (x from 40% to 60%, y from 20% to 80%) is at least 250, where the torso stands.

These regions follow the composition the prompt template fixes, not pixel-exact output, so re-running the tool with a newer model passes as long as the cut is sane.

Alternative considered: a pixel-exact golden file. It would be brittle across model versions and would test the tool rather than the contract.

### D5. Face rectangles are re-authored, not preserved

Regenerated figures are new renders on a 768×1024 canvas; the old rectangles were authored against 920×1536 pixels and make no claim about the new composition. After the six images are committed, each key's `FALLBACK_FACE_RECTS` entry is re-measured on the new pixels (normalized unit-square rects, same structure as today). The existing face-rect shape tests keep passing because only the numeric values change.

### D6. User-directed prompt correction

Live authoring exposed figures that were too small, dark and yellow. The user
identified the shared portrait wrapper, not the subject sentence, as the cause.
Correct `art.portrait_prompt` centrally: near-edge head/feet framing with a clear
margin, bright neutral daylight and fill, and true-to-life colors. The user withdrew
the experimental `,full body,` tag; full-body framing stays natural-language prose.
All image-level framing, size, lighting and palette instructions
belong only in the shared template; authored descriptions carry identity, clothing
and pose, without per-character color or image-size overrides. Both character and monster runtime
generation use `render_prompt_pair` and inherit this fix; scenes retain their
existing positive prompt. Following the requested image-prompt-builder-nl skill,
the portrait template is one folded natural-language paragraph, and exclusion
instructions live in `art.negative_prompt`, not the positive portrait prose.
The shared negative already forbids text and watermarks; explicit readable-text
and lettering negatives clarify that same constraint for both subject kinds.
Visual review of real generated output establishes the result,
not tests pinning incidental prose. Existing literal-word tests are removed,
while request and cutout-setting behavior tests remain.

## Risks / Trade-offs

- [The model eats a thin edge, such as hair strands or the monster's ragged cloak hem] → Task 2.2 has a person check each output on a dark (`#0b0d10`) and a light (`#e7e0d1`) background. A bad edge is re-run with `--key` (new seed); the prompt already bans backdrop shadows and detailed backgrounds, so regeneration is the first remedy. If repeated seeds keep failing, that one file is touched up by hand, and the contract test still guards the result.
- [An RGBA WebP is larger than the RGB one] → The configured quality knobs keep each file under 400 KiB (the RGB files are 42–63 KiB). The tool refuses to write a file at or over the bound.
- [Generation needs a reachable sd-webui server] → This is a one-time authoring action with an explicit operator prerequisite in tasks 2.1; the committed result leaves no runtime dependency. The gallery-art design already records the six license-clear images as a standing authoring obligation.
- [Browsers that cannot decode alpha WebP] → Every desktop browser in scope decodes WebP alpha. The project is desktop-only (design §2).

## Migration Plan

None. The files are replaced in place and there are no users. To roll back, restore the previous six files and the previous `FALLBACK_FACE_RECTS` values from git.
