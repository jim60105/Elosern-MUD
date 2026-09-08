# Character Gallery Art Design

Date: 2026-09-08
Status: approved by the project owner in a brainstorming session

## 1. Problem and current state

The art pipeline (`world/art/`) is single-asset: one `ArtAssetRecord` per
subject, one fixed output identity (`portrait/character/<key>.<ext>`), one
generation trigger (the `portrait_policy` ensure seam at creation/spawn/startup
recovery), and one deterministic prompt (registry fields plus the persona
`appearance` block). There is no way for a user to:

- generate several images for one character and keep/delete/select among them;
- choose which data the prompt includes (persona appearance, equipped items)
  or append free-form custom prompt text;
- bind an image to an equipment configuration and swap images when the
  configuration changes;
- mark where the face sits, so square avatar crops show the face;
- supply any art at all when SD is offline (the placeholder chain currently
  ends at "尚未生成").

Equipment (`world/skills/equipment.py::EquipmentHandler`) is never consulted by
any generation path. Avatar surfaces crop the 3:4 portrait with CSS
`object-fit: cover` at the default center anchor, which only statistically keeps
the face in frame.

## 2. Decision summary

| # | Decision |
|---|---|
| D1 | The gallery lives inside `world/art/` as a new layer reusing the existing queue, worker, SD client, format encoding, and path confinement (Approach A). No parallel subsystem, no subject-key abuse. |
| D2 | One `GalleryRecord` per subject holds an image-card list plus a `default_image_id`. Subjects: player, companion (an NPC), NPC, monster. |
| D3 | A generation job is queued under a per-image job key (`art:<subject>:gen:<image-id>`); the worker writes `gallery/<kind>/<subject-key>/<image-id>.<ext>` and the settle step appends the card. The first card of a subject becomes its default. |
| D4 | Each card stores the reproduction set: full positive and negative prompt text plus the server-reported seed, and the active checkpoint when one was configured. Environment-driven generation parameters (steps, cfg, dimensions, sampler, scheduler) are NOT stored. |
| D5 | An optional card `binding` is a slot mask plus a normalized equipment snapshot over the masked slots. An all-empty snapshot ("no equipment") is a legal binding. |
| D6 | Display resolution is a deterministic chain: current-snapshot mask match (most-specific mask wins; tie → newest `created_at`) → subject default → built-in fallback image. |
| D7 | Auto-generation (runtime LLM characters, quest characterization, startup recovery, player creation) is RETAINED as a character-creation step, but its image lands in the gallery as an unbound card with the fixed face-rect constant. Player creation may skip it; skipping falls back to the default/fallback chain. |
| D8 | Monsters use the same model with a one-card cap (regenerate replaces) and no binding. Companion-before-NPC ordering is a presentation concern only. |
| D9 | Face position is a normalized `{x, y, w, h}` rectangle on the card. The user draws it in the (future) UI; auto-generated cards get the fixed upper-half constant. NO automatic face detection. Avatars are rendered by CSS offset of the same image; the server never crops or stores a second image. |
| D10 | Seed art (bulk prebuilt template/NPC/player-template images) lives OUTSIDE git in an external directory mounted read-only (`ART_SEED_DIR`, the `PROMPTS_DIR` precedent) and is copied idempotently into the store at startup. Built-in fallback images (a handful) DO live in git and are served as static assets without copying into the store. |
| D11 | Generated and synced images stay under `ART_STORE_ROOT` (`server/.art/`, already gitignored, already a named volume). Runtime art never enters git. |
| D12 | This proposal is backend-only: service layer + seams + payload exposure. Frontend gallery/management UI is recorded as intent (D9 consumption, binding form, face-rect drag select) and left as TODO while the Vue rewrite is in flight. |
| D13 | Generation while SD is offline is a reported-unavailable error path; the resolution chain is independent of the generation path, so the AI-offline playability requirement is unaffected. |
| D14 | No player-facing commands are added in this proposal, so `docs/game/commands.md` is untouched. |

## 3. Data model

New modules under `world/art/` (`gallery.py` for the record + cards,
`gallery_match.py` for the resolution chain, `gallery_seed.py` for startup
sync). Record style follows `ArtAssetRecord` (a `DefaultScript` keyed
`gallery:<full-subject-key>`).

### 3.1 Image card (plain dict inside the record)

| Field | Shape | Notes |
|---|---|---|
| `image_id` | uuid string | stable card identity |
| `stored_identity` | `gallery/<kind>/<subject-key>/<image-id>.<ext>` | relative to `ART_STORE_ROOT`; reuses the existing confinement validation |
| `prompt` | `{positive, negative}` verbatim text | D4 reproduction set |
| `seed` | `int \| None` | server-reported seed, same tolerance as today |
| `checkpoint` | `str \| None` | recorded only when `ART_SD_CHECKPOINT` was set |
| `requested_fields` | list of field ids | which data blocks the user ticked (provenance only) |
| `face_rect` | `{x, y, w, h}` floats in [0,1] | validated: x+w ≤ 1, y+h ≤ 1, w,h > 0; fixed constant when auto-generated |
| `binding` | `None` or `{mask, snapshot}` | D5; `None` = never auto-selected by equipment, default-candidate only |
| `created_at` | float epoch | tie-break key |

`binding.mask` is a non-empty subset of `weapon_main`, `weapon_off`, `armor`,
`accessories`. `binding.snapshot` maps each masked slot to the normalized
current value: a string item key (single slots) or a sorted list of keys
(accessories). Mask selection is exactly "the user ticks which slots index this
image" (e.g. armor+weapon, armor+accessories).

### 3.2 GalleryRecord

- `cards: list[dict]` (append-ordered; monster cap = 1, enforced at append)
- `default_image_id: str | None` — first appended card auto-becomes default;
  an explicit set must name an existing card
- `kind` + `subject_key` mirror the `ArtAssetRecord` fields

Records are created lazily (on first card append / explicit default set), not
by startup scan. Subjects with no record resolve straight to the fallback.

### 3.3 Card deletion

Deleting a card removes it from the list and deletes its stored file under the
confinement rules. Deleting the current default clears `default_image_id` back
to `None` (chain falls through to remaining cards' absence → fallback), never
dangling.

## 4. Generation pipeline

### 4.1 Request

`request_gallery_image(entity_or_subject, *, fields: tuple[str, ...], custom_prompt: str, binding=None, face_rect=None)`
(service layer, post-commit ensure like today):

1. Validate subject, field ids, custom-prompt bound, face rect, binding shape.
2. Assemble the prompt: the existing `art.portrait_prompt` +
   `character_description` base, plus one fragment per ticked field — the
   persona `appearance` block (existing `_appearance_fragment`) and, when
   equipment fields are ticked, the equipped items' `ItemPresentation`
   visual text from `world/lore/items.py` (registry-owned, read-only). Then
   append the user's free text. Negative prompt unchanged.
3. Mint `image_id`, enqueue a job keyed `art:<full-subject>:gen:<image-id>`
   carrying the assembled prompt, the id, and the pending card metadata
   (fields, binding, face_rect) in the queue record.
4. The SD client sends the request as-is; `GeneratedImage` provenance fields
   already carry the exact prompt pair and seed.

All SD-transport states settle FAILED on the job record without touching the
gallery — a failed generation appends no card.

### 4.2 Worker and settle

The worker writes the PNG bytes to the per-image gallery path (same atomic
write, extension via `ART_SD_OUTPUT_FORMAT`). Settle appends the card to the
`GalleryRecord` in one transaction: file write first, card append second, so a
crash leaves an orphan file (harmless, reclaimed by a prune sweep at startup)
rather than a card pointing at a missing file.

### 4.3 Auto-generation retrofit (D7)

`schedule_portrait_ensure` / `schedule_occupant_portrait` / startup recovery
keep their eligibility checks (canonical ages, explicit `portrait_policy`) but
route through `request_gallery_image` with `fields=("appearance",)`, empty
custom prompt, `binding=None`, fixed face rect. Player creation keeps
`finalize_player_portrait` but threads an explicit skip flag; skipped creation
simply starts with an empty gallery and resolves via fallback. Quest
characterization and monster-tier startup ensure behave likewise.

### 4.4 Offline behavior (D13)

`request_gallery_image` checks SD availability the way the existing queue
drain does and raises/returns a named unavailable result without queueing.
Nothing in §5 depends on generation ever having succeeded.

## 5. Resolution chain (presentation)

`resolve_entity(entity)` gains gallery resolution while keeping every current
placeholder kind:

1. Compute the four-slot snapshot from `EquipmentHandler` (accessories sorted;
   empty = legal).
2. Candidates = cards whose binding mask values all equal the snapshot.
3. Most mask slots wins; tie → newest `created_at`.
4. Else `default_image_id` card.
5. If no mask matched and no default is set, the chain falls through even when
   unbound cards exist — an unbound card is never shown as a surprise.
6. No eligible card → built-in fallback image (§7).

The payload becomes `{url, face_rect, kind}` (`url` may be the fallback
static URL); `face_rect` is the D9 rectangle or the fixed constant. Monsters
resolve through the same chain minus step 1–3 (no binding). The presenter stays
the sole URL-issuing boundary: gallery paths go through the same
symlink/path-confinement validation as today.

## 6. Face rect and avatar (D9)

- Constant `DEFAULT_FACE_RECT = {x: 0.25, y: 0.06, w: 0.5, h: 0.5}` (upper-half
  anchor) — used for auto-generated cards and for any card lacking a rect.
- The server stores the rect verbatim; it never transforms or crops images.
- Avatar surfaces (future UI) map the normalized rect to CSS
  (`object-fit: cover` plus `object-position` computed from the rect center),
  so 1:1 frames show the marked face. This replaces the current blind
  center-crop behavior noted in §1.

## 7. Seed art and built-in fallbacks (D10, D11)

### 7.1 External seed directory

- `ART_SEED_DIR` (env-overridable, empty default = feature off), bind-mounted
  `:ro,z` in compose exactly like `PROMPTS_DIR`. Local default directory
  `art-seed/` added to `.gitignore`.
- Layout: `art-seed/<kind>/<subject-key>/<filename>.png` plus an optional
  `manifest.json` per subject (`{"default": "<filename>", "face_rect": ...}`);
  absent manifest → first file by sorted name is default, fixed face rect.
- `gallery_seed.sync_all()` runs at startup idempotently (lore-mirror
  pattern): copies each seed file into the store gallery path and appends a
  card (unbound, seed provenance = `{"source": "seed"}`, no prompt pair).
  Re-running never duplicates. A missing/broken seed directory logs one
  `gallery_seed_sync` event and skips — never a startup failure.
- Seed cards are regular cards: user-deletable, default-settable.

### 7.2 Built-in fallback set (in git)

- A handful of static images in the served static tree
  (`web/static/art/defaults/`), keyed `man`, `woman`, `boy`, `girl`, `elder`,
  `monster_anon` (extensible), with a fixed static face-rect constant map.
- Registry-optional declaration: player presets and NPC/monster registry data
  MAY declare a fallback key; unregistered/undeclared subjects resolve
  deterministically by hashing the subject key into the pool matching the
  declared sex/age band (monsters → `monster_anon`). Same subject, same image
  across restarts.
- Served directly as static assets; NOT copied into the store. Guarantees art
  on a fresh database with every external service offline.

## 8. Frontend intent (TODO — out of this proposal's scope, D12)

Recorded intent only; the Vue rewrite owns implementation:

1. Consume `{url, face_rect}` everywhere a portrait/avatar renders; avatar
   frames CSS-offset by the rect (§6).
2. Gallery manager: image grid, keep/delete, set-default, binding mask/snapshot
   editor, drag-rect face selection, generation form (tick data fields —
   persona appearance, each equipment slot — plus free prompt).
3. Roster ordering: active party companions before other NPCs.
4. Until the manager ships, the backend still exposes resolution results and
   `face_rect` through the existing frame/payload surface; management ops run
   through the service API seam.

## 9. Error handling and observability

- Every boundary event per the observability catalog: `gallery_generate`,
  `gallery_settle`, `gallery_seed_sync`, `gallery_fallback_used`; business ids
  (`subject`, `image_id`, `kind`) in `context`, facade-only logging, lint-clean.
- Validation failures (bad rect, bad binding, monster cap, unknown field id)
  raise typed errors at the service boundary; queue/worker failures settle the
  job only.
- All card/record parsing is tolerant: a malformed stored card is skipped by
  the chain (logged once), never a crash — mirroring the existing placeholder
  degradation philosophy.

## 10. Testing

- Pure `unittest.TestCase`: snapshot/mask matching (specificity wins, tie →
  newest, empty-equipment binding, no-match → default → fallback), face-rect
  and binding validation, monster one-card cap, fallback hash determinism and
  pool-band correctness, seed manifest parsing.
- Evennia integration: worker settle appends exactly one card and writes under
  the confined path; failed generation appends none; startup seed sync is
  idempotent and crash-free on a broken directory; auto-generation retrofit
  produces an unbound fixed-rect card; player-creation skip leaves the gallery
  empty; presenter payload carries `face_rect`.
- Traceability: new main-spec requirements get `@covers_requirement`; new test
  modules register in `.github/evennia-shards.json` in the same change.
- JS gates: untouched (frontend TODO); Node/Vitest/Storybook suites unchanged.

## 11. Explicitly out of scope

- Face detection, server-side cropping, second avatar asset.
- Frontend gallery UI implementation (intent only, §8).
- Any new player-facing command or `docs/game/commands.md` change.
- LFS adoption.
- Backward-compat shims for pre-existing single-portrait outputs (no released
  users; the migration is simply "re-resolve": old fixed-identity files remain
  readable until deleted, but new resolution reads only galleries).
