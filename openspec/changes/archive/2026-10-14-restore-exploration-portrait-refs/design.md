# Design

## Context

See `proposal.md` for motivation. Fresh source confirms `exploration.py` version 3 rejects non-null refs and hard-codes null in `_look_entities` and `_interact_targets`; the JS mirror repeats that restriction and `protocol/constants.js` advertises version 3. The registry imports the Python constant. `exploration_menu.js` already preserves target references, with entity fallback, and `PresenceRail.vue` resolves `portraitRef` through `portraitFor`, tracks failed URLs and crops `face_rect`. `use-person-focus.js` already reads the focused interact reference reactively and passes the raw catalog entry to `StageActor`.

`world/rules/art_view.py` is the membership owner. Exploration candidates are sorted dialogue hosts or named-policy characters excluding the actor, followed by co-located live owner companions in party order, deduplicated and capped at 32. Possessed companions are re-added through the owner party; generic monsters and ordinary unconfigured characters are not automatically catalogued. A real resolved image alone does not establish catalog membership. `art.py` serializes that view through `resolve_entity`; `party.py:_resolve_portrait_ref` delegates real-image eligibility to that same chain and excludes decorative silhouettes. Keep that precedence, canonical-age checks and membership unchanged.

`art_push.py:_push_for_subject` currently publishes only qualifying art/gallery/roster panels. Its existing current-state subject gate is suitable for late-completion safety, but exploration null references would remain stale after a pending portrait becomes real. The architectural source of truth, engine design §8, keeps presenters read-only and queue writes in their existing lifecycle owners.

## Goals / Non-Goals

**Goals:** connect the exact exploration wire to admitted catalog imagery and preserve functional exploration through missing/failed art; update descriptors on existing completion publication.

**Non-Goals:** enlarge the catalog, change monster/character eligibility or party references, fix duplicate companion focus, change art generation/selection/media routing, add general retry machinery, or migrate saved data.

## Decisions

### D1. One exact schema-4 cutover

Advance Python `EXPLORATION_SCHEMA_VERSION` and JS `PANEL_SCHEMAS.exploration` to 4; update validator comments, existing fixtures and all authored available payloads/callers. Both descriptor validators accept null or an unchanged ASCII `[0-9]+` string of 1..32 characters, matching the party/combat reference seam. Validators check shape and bound, never coerce values or cross-join an independently delivered art panel. Numeric, empty, overlong, Unicode-digit, URL-like and subject-key values reject. Exact field sets, action vocabulary, list limits and envelope-size checks remain intact; test maximum-length refs as part of the existing worst-case envelope case. Reject schema 3 and every other available version. Common unavailable forms remain the registry's responsibility.

Keeping version 3 while expanding accepted values hides a contract change. A dual-version adapter adds unused maintenance to this unreleased project.

### D2. Use current art-view membership plus canonical real-image resolution

Build `build_art_view(actor)` once per exploration presentation and a membership set from its capped entities. Resolve a descriptor only when its identity belongs to that set. Use `resolve_entity` once per relevant identity per render and reuse its result across look/interact paths; emit `portrait_catalog_key(identity)` only for an own non-null media URL with origin runtime or official. Reuse the real-image gate semantics from party without importing a private party function or cloning source precedence. A small exploration-owned per-render lookup is sufficient; no persistent/global cache or new art service is needed.

Both lists retain their canonical candidate, visibility, ordering and cap rules. An entity appearing in both lists receives the same ref. A catalogued named character outside interact gets its image-bearing bystander medallion; an unconfigured character, ordinary monster or cap-dropped identity stays null even if standalone resolution could find an asset. This change guarantees every emitted non-null ref joins the normal art view for the same actor; it does not promise every room entity gets a catalog row. If the art view is unavailable, degrade only refs to null through the existing explicit art-unavailable boundary and keep the exploration panel/actions available. No broad catch that hides producer errors.

Cross-panel resolution uses the same read-only chain. Snapshot and focused producer tests compare actual emitted refs to the separately rendered art catalog, including cap pressure and possession. Do not infer a key in the browser or join party to paper over a missing exploration descriptor.

### D3. Refresh only exploration descriptors affected by portrait completion

Retain `_push_for_subject`'s freshly rendered matching art/gallery/roster panels and one `panel_update`. If the matching art catalog contains the completed portrait subject and current mode is exploration, render the available exploration panel and include it in the same update. A scene-only art match adds no exploration panel. An absent/unavailable exploration panel is omitted so art completion remains isolated. No new subscription, full-snapshot broadcast or second revision is needed. The current-state art gate excludes old-room/departed subjects; a reconnect still gets a fresh full snapshot.

This extra bounded render is necessary because D2 intentionally leaves imageless descriptors null. Keeping placeholder refs would depart from the real-image gate; client-side key synthesis would violate the authoritative seam. Test a real pending-to-done completion that changes the descriptor from null, plus a late completion that publishes no stale exploration. Existing observation logging remains through its current facade.

### D4. Preserve consumers and truthful fallback

Use existing `presenceEntries`, `portraitFor`, `face_rect`, `StageActor` and `ReferenceArtwork`. Make consumer edits only where an end-to-end regression exposes a gap. Null/unknown/unavailable entries use the name initial on medallions and established stage placeholder for non-party focus; failed image loads retain that treatment. A newer catalog URL is eligible to render after failure of the old URL, and an already-open focus updates its portrait without reopening or dispatching. A same failed URL is not automatically retried; no retry policy is added.

Storybook samples must use valid decimal refs and current schema fixtures, with comments distinguishing synthetic rendering from production protocol evidence. Live proof must inspect the actual producer packet, admitted catalog URL, `img.complete` and nonzero `naturalWidth`; a DOM `img` alone is insufficient.

## Acceptance and Evidence Plan

| Boundary | Observable defect detector |
| --- | --- |
| Python/JS exact validation | Accept null and 1/32-character decimal refs in both paths; reject malformed refs and old versions; preserve unknown-field/byte-limit rejection |
| Production producer/catalog | Synthetic official/runtime admitted image joins both descriptor paths; excluded and cap-dropped controls stay null; eligibility rejection emits no real ref; before/after canonical state and art records unchanged |
| Completion publication | Pending-to-done current portrait includes exploration plus art in one newer update; unrelated/scene-only/departed subjects do not publish stale descriptors |
| Accepted store/component boundary | `store.receive` accepts a schema-4 snapshot before medallion face and non-party standee image assertions; cover bystander, null, unknown key, unavailable, failed load and changed-URL recovery |
| Storybook/live | Existing presence and AppShell examples exercise valid refs; agent-browser at 1451×790 and 1920×1080 proves actual loaded media, face crop and non-party focus; record only read-only runtime observations and approved existing talk/back actions |

Use synthetic mechanism fixtures, not shipped names/IDs. Existing test modules are `test_exploration_panel/test_schema.py`, `test_presenter.py`, `web/webclient/tests/test_art_push.py`, Node `protocol_exploration_a/b.test.js`, `exploration_menu.test.js`, Vitest `app_client_presence_rail.test.js` and `tests/world/presence_rail.test.js`. Reuse existing browser navigation seed/helper infrastructure and real server-origin fixture media. New browser methods must be registered in `.github/browser-shards.json`; no new Python module is planned, otherwise update `.github/evennia-shards.json`. Update relevant protocol documentation and annotate matching traceability tests at spec sync using IDs obtained from the CLI.

## Risks / Trade-offs

- Catalog cap excludes a valid image-bearing entity -> preserve the cap and emit null; test overflow against actual membership, rather than expanding scope.
- Independent art panel failure leaves a syntactically valid reference unresolved -> browser fallback remains functional; only normal successful production catalog rendering promises the join.
- Repeated image-chain reads for look/interact -> reuse per-render resolution by identity and the once-built art membership set.
- Completion refresh could over-publish scene changes -> add exploration only for a current portrait-catalog subject match in exploration mode and keep one revision.
- Eight-hour boundary -> extend existing tests/fixtures and rendering, avoid catalog redesign and media retry policies; budget is in `proposal.md`.

## Migration Plan

Deploy producer and JS schema-4 bundle together; normal reconnect obtains a current snapshot. No data migration or compatibility adapter. Operational rollback restores both code and bundle together. This proposal does not perform deployment, application or archive.
