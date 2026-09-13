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

> Superseded during decomposition — see §12.3.1: the request never probes; an
> unreachable server is a bounded failed settle that appends no card.

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

> Not delivered by the change decomposition — see §12.4: the rectangle ships,
> but no change wires it into the live client's avatar frames.

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

> Refined during decomposition — see §12.3.3: the set is served through the
> `/art/defaults/<key>.<ext>` route rather than as raw static assets.

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

> Refined during decomposition — see §12.3.2: the resolution chain keeps the
> classic asset record as one lower-priority step, so nothing needs migrating.

- Face detection, server-side cropping, second avatar asset.
- Frontend gallery UI implementation (intent only, §8).
- Any new player-facing command or `docs/game/commands.md` change.
- LFS adoption.
- Backward-compat shims for pre-existing single-portrait outputs (no released
  users; the migration is simply "re-resolve": old fixed-identity files remain
  readable until deleted, but new resolution reads only galleries).

## 12. Change decomposition (OpenSpec proposals)

Written 2026-09-08 after this design was approved. The design above is the
contract; this section records how it was carved into independently shippable
OpenSpec changes, in what order they may run, and the three points where the
decomposition deliberately departs from the text above.

### 12.1 The seven changes

| # | Change | New capability | Scope | Depends on |
|---|---|---|---|---|
| 1 | `gallery-card-model` | `art-gallery-model` | `world/art/gallery.py`: `GalleryRecord`, the card contract, face-rect and binding validation, the no-create equipment snapshot reader, the monster one-card cap, the single-writer boundary, tolerant reads. Plus `world/art/paths.py`, the one store-root confinement helper. | — |
| 2 | `gallery-generation-jobs` | `art-gallery-generation` | Per-image job records keyed `art:<subject>:gen:<image-id>`, job-key-resolved settle, record-derived output identity, settle-as-card-append, spent-job deletion, orphan prune at startup, `gallery_generate` / `gallery_settle`. Request seam without field selection. | 1 |
| 3 | `gallery-prompt-composition` | `art-gallery-prompt-fields` | The closed field catalog (`appearance` plus the four equipment slots), `ItemPresentation` fragments, the bounded free-text field, `requested_fields` provenance, the two new `art.character_description` slots. | 2, 7 |
| 4 | `gallery-resolution-chain` | `art-gallery-resolution` | `world/art/gallery_match.py`, presenter integration, the `gallery/` and `defaults/` media-route branches, `face_rect` on every payload and in the `art` / `roster` wire validators. | 1 |
| 5 | `gallery-builtin-fallbacks` | `art-gallery-fallback` | The six committed images, the closed key vocabulary, declaration → sex/age band → deterministic hash resolution, the per-key rectangles, `gallery_fallback_used`. | 4 |
| 6 | `gallery-seed-sync` | `art-gallery-seed-sync` | `ART_SEED_ROOT`, the compose `:ro,z` mount, the gitignore entry, `world/art/gallery_seed.py::sync_all()`, path-derived idempotency, the optional per-subject manifest. | 1 |
| 7 | `gallery-autogen-retrofit` | `art-gallery-autogen` | The D7 retrofit: every automatic character path routes to the gallery as one unbound appearance-only card, gallery-based idempotency, the player-creation skip flag, the `@art requeue` character branch. | 2 |

Modified existing capabilities: `art-queue-worker` (by 2 and 4, different
requirement blocks), `art-subject-model` (by 3), `container-image` (by 6),
`art-asset-lifecycle`, `spawn-named-portraits`, `art-staff-commands` (by 7),
`webclient-art-panel` and `webclient-character-roster` (by 4).

Each change is sized for roughly one engineer-workday.

### 12.2 Parallel batch order

- **Batch 1** — `gallery-card-model`. Every other change builds on the card
  contract, so it lands alone.
- **Batch 2** — `gallery-generation-jobs`, `gallery-resolution-chain`. The first
  owns `queue.py` / `worker.py` / `service.py`; the second owns `presenter.py` /
  `web/art_media.py` / the webclient payloads. No shared files.
- **Batch 3** — `gallery-builtin-fallbacks`, `gallery-seed-sync`,
  `gallery-autogen-retrofit`. Each depends on a batch-1 or batch-2 change and
  touches a distinct area (the fallback set, settings/compose/startup, and the
  auto-generation seams respectively).
- **Batch 4** — `gallery-prompt-composition`, alone. It must land AFTER
  `gallery-autogen-retrofit`: both rewrite
  `world/art/service.py::_ensure_character_portrait` and the startup recovery
  scan, and this change's job there is to make the already-retrofitted request's
  field selection explicit. Running the two in parallel is a guaranteed rewrite
  conflict in the same functions. `gallery-autogen-retrofit` is written so it does
  NOT need the `fields` keyword this change introduces.

Known coordination points:

- `gallery-generation-jobs` and `gallery-seed-sync` each add one startup step to
  `server/conf/at_server_startstop.py` (a two-line merge if they overlap).
- `gallery-generation-jobs` and `gallery-resolution-chain` each carry a delta for
  the `art-queue-worker` capability, but for different requirement blocks; archive
  them in landing order.
- `gallery-builtin-fallbacks` carries an authoring dependency outside the code:
  six license-clear images (`man`, `woman`, `boy`, `girl`, `elder`,
  `monster_anon`), size-bounded, with no sexualized content in any of them. It is
  the one change engineering cannot finish on its own.

### 12.3 Deliberate deviations from this design

1. **§4.4 offline probe → reported failure.** `request_gallery_image` does NOT
   probe sd-webui availability. Probing would require a module under `world/art/`
   other than `connectivity.py` to import `world.art.connectivity`, which the
   `art-service-connectivity-surface` requirement forbids and an import-boundary
   test enforces. Instead the request enqueues unconditionally; an unreachable
   server settles the job `failed` with its existing bounded named error code,
   appends no card, and records that code on the `GalleryRecord`. This delivers
   D13's actual guarantee — a reported unavailable outcome with the resolution
   chain untouched — without breaking the connectivity boundary.
2. **§11 "new resolution reads only galleries" → one extra chain step.** The
   resolution chain keeps the classic `ArtAssetRecord` `done` asset as the step
   after the subject default and before the fallback. Monsters, scenes, and any
   not-yet-migrated portrait therefore keep resolving exactly as they do today,
   and the retrofit needs no migration at all. The cost is one strictly
   lower-priority step in the chain.
   Monsters stopped PRODUCING classic records with `gallery-monster-autogen`
   (§12.5): their generation reached the gallery like the character's.
   Already-existing classic monster records keep resolving through this step
   and are never migrated, reset, or newly produced — the deviation stands for
   them.
3. **§7.2 static serving → the `/art/defaults/` route.** The built-in fallback
   images are served through the existing `/art/` route from a fixed in-repo
   defaults directory rather than as raw static assets, so `/art/...` stays the
   single media URL vocabulary the wire validators accept and one confinement
   discipline covers every served image.

Two naming refinements, both following the `PROMPT_ROOT` / `PROMPTS_DIR`
precedent §7.1 cites: the engine setting is `ART_SEED_ROOT` (read from the
environment variable of the same name, defaulting to `<GAME_DIR>/art-seed`),
while `ART_SEED_DIR` stays the compose-only interpolation variable for the host
bind mount. The gallery store path's `<kind>` segment is the closed set
`character` / `monster`, so a stored identity is always four path segments.

### 12.4 Known gap: face_rect ships with no live consumer

D12 was written on the premise that the Vue rewrite had left no frontend to
integrate with. That is not the current state: `web/webclient-app/` is the
production client, and `ArtPanel`, `ParticipantFrame`, `CharacterSwitcher`,
`PartyStrip`, `PartyDrawer`, and `NarrativeFeed` all render portraits with
`object-fit: cover` — exactly the blind centre crop §1 and §6 set out to replace.

Adding `face_rect` to the payload is additive and safe for that client (it reads
entries by key and performs no `schema_version` check), but none of the seven
changes wires the rectangle into a CSS offset. D12's deferral stands, so the
consequence is recorded rather than resolved: **§6's avatar behaviour is NOT
delivered by this decomposition** and needs a separate frontend change once the
rewrite settles.

### 12.5 Closed: monster generation reached the gallery

The decomposition (§12.1–§12.3) shipped monsters as D8 says: still generated
classic — every `MONSTER_TIER_REGISTRY` tier got one generic prompt, one card,
no player trigger, and startup synchronization wrote each tier a classic
subject-keyed record. `gallery-monster-autogen` lands the routing D8 deferred
behind the card model: startup synchronization now requests a guarded gallery
generation for every tier through the ONE shared automatic-ensure helper
(`_ensure_gallery_subject`, formerly `_ensure_character_portrait`), the classic
generic-monster record is retired from production — the scene kind is the only
classic-record producer on any path (`@art retry`'s classic arm likewise skips
gallery-bearing kinds) — and pre-existing monster records are left in place,
resolving through the display chain's classic step (the §12.3.2 qualification
stands for them). Startup order moved to prune → seed → sync so a seed card
always occupies a tier's gallery before the automatic guard reads it. D8's
cardinality outcome is unchanged: the monster kind's declaration caps the
gallery at one card, so each tier still holds one generated image — through
the gallery now, not the classic table.

### 12.6 Gallery management read model

`webclient-gallery-panel` adds the exploration-only `gallery` v1 presentation
panel. It does not add the Vue management screen or action registrations;
those remain owned by `webclient-gallery-ui` and `webclient-gallery-actions`.
The four `docs/design/elosern-redesign2/角色肖像圖庫管理頁-*.webp` references
define that future screen's gallery grid, face editor, equipment drawer, and
generation drawer. This panel supplies their server-authored display facts.

The rail is a world-gallery view bound to the current puppet, not an account
roster. It reserves space for the puppet and all monster tiers within 24 rows,
then fills character places companion-first and by numeric entity primary key.
Selection is immutable session `ndb` state bound to puppet and presentation
epoch; `select_gallery_subject(session, actor, subject_key)` returns result data
without sending. The future action adapter owns publication. Disconnect's
unpuppet signal, explicit unpuppet, coordinator reset, and puppet switch retire
selection. A deleted selected character falls back to the puppet during render.

Cards require a valid own-subject store identity and an existing confined file.
The panel derives chips, exact filter counts, one equipment snapshot, and up to
five current-match warnings. Accessory comparison remains exact normalized
equality; the design's 「任一」 wording is presentation only. A read-only queue
accessor supplies up to eight pending rows; a recorded generation failure
becomes one deterministic synthetic row, without a service probe.

`record_for(create=False)` is now genuinely read-only, including when duplicate
records exist. Consolidation remains on the locked gallery write paths. Character
cards are not silently truncated; an oversized payload fails closed at the
existing 65,536-byte envelope boundary. The UMD validator, its Vue wrapper, and
the Vue store accept the new panel without introducing a client matching engine.
`test_gallery_panel.py` covers read-only behavior, lifecycle retirement, missing
and symlinked media, offline failure settlement, and executable Python/Node
boundary parity; panel schema enumeration and shard ownership include it.

### 12.7 Gallery management actions

`webclient-gallery-actions` exposes six exact `ui_action` adapters:
`gallery.subject.select`, `gallery.generate`, `gallery.default.set`,
`gallery.card.delete`, `gallery.face_rect.update`, and `gallery.binding.save`.
These are webclient-only controls with explicit silence in the command-echo
catalog, not new text commands (D14). The separate gallery UI change owns
buttons, drawers, and local face previews; no Vue component ships here.

Selection calls the panel's rail store and changes only transport/puppet/epoch
presentation state. The dispatcher publishes one gallery update before its
result. Mutations re-resolve live character objects or typed monster tiers and
use only the public art APIs. Named cards must survive `cards_for`'s tolerant
read. Binding captures currently worn equipment at save time, sorts accessories,
retains enabled empty slots, and orders the mask by backend `SLOT_ORDER`;
client payloads carry only slot ids, never item keys. Face saves preserve the
rectangle and the card's image identity/provenance without touching files.
Generation returns the minted image ID after enqueue; offline failure and
monster replacement are still worker-settlement outcomes.

The Python schemas and exported JS `validateGalleryActionPayload` mirror exact
keys, the rail grammar, canonical lowercase UUIDs, catalog/slot bounds, and
positive finite unit-square rectangles (booleans are not numbers). Prompt
limits count Unicode code points before normalization. The shared backend
validator rejects every Unicode C/Z category except ASCII space, including
non-breaking spaces and line separators. Only the service normalizes accepted
prompt whitespace and catalog order.

Schema violations return `malformed_payload` without entering an adapter or
emitting `gallery_action`. Domain results have bounded zh-TW messages and the
following stable codes:

| Code | Meaning |
|---|---|
| `unknown_subject` | The current rail selection or live/typed subject resolution failed. |
| `unknown_card` | The named card is absent or unreadable through the tolerant read. |
| `field_selection_unsupported` | Valid prompt fields were supplied to a kind without field selection. |
| `free_text_unsupported` | Nonempty printable prompt text was supplied to a kind without free text. |
| `binding_unsupported` | The resolved kind has no binding support; this precedes card lookup. |
| `subject_ineligible` | A resolved subject failed a generation precondition, such as missing canonical ages. |
| `unknown_field`, `prompt_too_long`, `invalid_prompt` | Defensive service-error mappings for direct adapter calls; wire-invalid values normally fail the earlier schema. |
| `gallery_rejected` | Other typed card-contract refusals, including invalid direct-call face coordinates. |

Each completed adapter emits one facade `gallery_action` event (info on
success, warn on domain rejection), with subject/action/kind/image identifiers
and exception context where present. Public service events remain separate.
Success and domain rejection target only gallery; replayed completed request
IDs execute neither the adapter nor its event again. Stale and busy handling
remain dispatcher-owned.

The deterministic action module tests exercise real records, public offline
queue settlement, dispatcher selection publication and retirement, and
Python/Node payload parity. Its shard owner is the existing recursive
`web.webclient.actions` label; adding a second module label would duplicate
ownership. New requirement annotations belong to archive-time main-spec sync;
apply annotates only existing matching requirements and leaves main specs alone.
