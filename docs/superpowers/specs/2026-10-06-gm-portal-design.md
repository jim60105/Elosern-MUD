# GM Portal Design

- Date: 2026-10-06
- Status: Approved design (roadmap + S1 detail)
- Scope: An operator-facing web portal under `/gm/` for inspecting game data,
  monitoring services, managing saves, and repairing world state through
  rule-backed operations. It is not part of the player experience; it is
  functional in design and shares the webclient's visual design system.

## 1. Purpose, goals, and non-goals

### Why a second interface

Elosern is single-player: the player and the operator are the same person in
two roles. The game webclient is deliberately in-character and immersive. NPCs
never name mechanics, vitals hide at full, and failed LLM calls degrade
silently so play continues. It exists to hide things from the player.

The portal is the out-of-character, omniscient view: it shows what the game
hides and does what the game deliberately does not let a player do. Keeping
that in a separate interface protects immersion while playing. The operator
switches to it:

1. When the experience goes wrong or feels wrong: the silent degradation leaves
   no trace in game, so diagnosis happens here (S2, S3). This is the primary
   use.
2. To see the truth behind the play: hidden identities, true traits behind
   disguises, NPC memories, story threads, scheduled beats (S3).
3. During authoring time outside play: content and balance work against the
   authored data and its references (S4).
4. Before experimenting: a world snapshot is the save slot (S5).
5. When a save is broken: there is no other GM to ask, and hand-patching state
   in a Django shell is forbidden, so repairs go through validated, audited
   operations (S6).

Multi-user server concerns (account administration, broadcasts, bans) are out
of scope.

### Goals

- One Developer-only entry point for operating the game: a monitoring
  dashboard, read-only inspection of runtime state and authored world data, and
  operations that route through the deterministic core.
- Visual consistency with the game webclient through the shared design tokens
  (`web/webclient-app/styles/tokens.css`, `fonts.css`).
- Strict isolation from the game webclient bundle, its frozen contracts, and
  the OOB protocol.

### Non-goals

- Editing authored world data (lore registries, rulebook YAML, quest catalog,
  prompts) from the web. Authored data stays version-controlled source; the
  portal only browses it. Changes are made in source files and go through git.
- Replacing Evennia's Django admin at `/admin/`. It remains untouched.
- Mobile-optimised layouts. The portal is desktop-first; narrow viewports must
  remain usable but get no dedicated design.
- Any direct field-level write to persistent state from `web/`.

## 2. Resource inventory

The portal manages three classes of resources.

### A. Authored world data (source in git, synced at startup, immutable at runtime)

| Category | Source |
| --- | --- |
| Races, subraces, nations, elements, magic | `world/lore/races.py`, `nations.py`, `elements.py`, `magic.py` |
| Monster species, tiers, placement | `world/lore/monster_species.py`, `monsters.py`, `monster_placement.py` |
| Item catalog | `world/lore/items/data_*.py` |
| NPC profiles and dialogue tables | `world/lore/npc_profiles/`, `world/lore/dialogue/` |
| Settlements, places, shops, assortments | `world/lore/settlements/`, `world/lore/church/` |
| Titles, player presets, starting kits, name corpus, scene archetypes, wilderness regions, anchors, guild ranks | `world/lore/*.py`, `world/lore/player_presets/` |
| Skill registry | `world/skills/` |
| Quest catalog | `world/quests/catalog.py` |
| Rulebooks | `world/rules/rulebook/*.yaml`, `world/rules/rulebook/commerce/` |
| LLM prompts | `prompts/*.yaml` |
| Official artwork catalog | `art-official/`, `art-seed/` |

### B. Runtime persistent state (database)

- Accounts and characters: Evennia accounts, `PlayerCharacter`, NPCs, monster
  individuals.
- World: grid rooms, instances, wilderness population, world clock, combat
  sessions.
- Quests: runtime quest records, `GeneratedQuestStore`.
- Narrative (`world/narrative/models.py`): `NarrativeEvent`, `MemoryRecord`,
  `MemoryRevision`, `StoryThread` and links/revisions, `DialogueTurn`,
  `DialogueEpoch`, `DialogueFrame`, letters (`LetterSend`, `LetterState`,
  `LetterReplyWork`), `DreamSession`, `DreamExchange`,
  `StoryDirectorDecision`, `ScheduledBeat`, `AuthoringDraft`,
  `CreativeRequest`, `NarrativeContextSnapshot`.
- NPC personas (persona store).
- Art: `ArtAssetRecord`, gallery records, generation queue, `ArtDrainScript`.
- Economy: wallets, shop stock.

### C. Operations and monitoring

- External service connectivity: LLM endpoints and profiles, sd-webui,
  translation (CTranslate2), cutout (rembg).
- Art queue: pending, failed, recently completed jobs.
- LLM calls: currently emitted only as `llm_call` log events.
- Live world state: clock tick, connected sessions, active combats and
  instances.
- Recent `log_error` events and `startup_step` outcomes.
- Effective settings overview (read-only).

### Existing management surfaces

- Evennia Django admin at `/admin/` (uncustomised, different visual style).
- The staff `@art` command family (`commands/art.py`).
- The in-game NPC persona editor.
- Developer-locked `charcreate` / `chardelete`.

## 3. Architecture

```
Browser /gm/*      web/admin-app/  (Vue 3 SPA, separate Vite build)
                     | imports only: web/webclient-app/styles/tokens.css, fonts*.css
                     v fetch JSON (same origin, Django session cookie, CSRF)
Django /gm/api/*   web/gm/  (Django app: views, access decorator, serialisation)
                     | reads: registries, ORM, typeclasses (read-only queries)
                     | writes: only named deterministic APIs
                     v
world/rules/, world/maps/, world/quests/, world/narrative/, world/art/
```

### Cross-cutting constraints (apply to S1–S6)

1. **Access.** Every `/gm/` page and `/gm/api/` endpoint requires an
   authenticated account for which `account.check_permstring("Developer")` is
   true (superusers pass). Unauthenticated page requests redirect to
   `LOGIN_URL` with `next=`; unauthenticated API requests return `401`;
   authenticated accounts without the permission get `403`.
2. **Single writer.** `web/gm/` never mutates persistent state itself. Every
   S6 game-state write maps to one named API in a single-writer package
   (`world/rules/`, `world/maps/`, `world/quests/`, `world/narrative/`);
   `web/gm/` only validates transport shape and forwards. S5 snapshots and
   restores operate below game rules through `server/saves/`, never through
   field-level writes.
3. **Authored data is read-only.** S4 reads module-level registries and loaded
   rulebooks. No code path writes source files. S4's prompt reload only
   re-reads `prompts/` into the in-memory library.
4. **Offline.** The bundle is served from the project origin. With LLM and SD
   services offline, the portal still loads and reports those services as
   offline.
5. **Observability.** GM writes emit facade events (`gm_action`) with the
   operator account and target identifiers in `context`. S6 additionally
   persists an audit record.
6. **Isolation.** The portal bundle is built and served separately from the
   game bundle. The webclient frozen contracts, `.elosern-root` styles, and OOB
   protocol are untouched.

### Sub-projects

Each sub-project is delivered as its own OpenSpec change (proposal, specs,
tasks) in this order.

| ID | Content | Depends on |
| --- | --- | --- |
| S1 | `web/gm/` app, access control, SPA skeleton, navigation, component layer, API envelope | — |
| S2 | Operations dashboard | S1 |
| S3 | Runtime state inspection | S1 |
| S4 | Authored data browser and cross-references | S1 |
| S5 | Save management: snapshot and restore of the world state | S1 |
| S6 | Save repair: new validated rule APIs plus audit trail, each preceded by an automatic snapshot | S1, S3, S5 |

This document specifies S1 in full. S2–S6 are scoped in §6; each gets its own
brainstorming pass before its OpenSpec change.

## 4. S1 backend (`web/gm/`)

### Routes

`web/urls.py` adds `path("gm/", include("web.gm.urls"))`.

| Route | Purpose |
| --- | --- |
| `GET /gm/` and `GET /gm/<path:rest>` | Serve the SPA shell template (client-side history routing). `rest` never matches the `api/` prefix. |
| `GET /gm/api/session` | Current operator: account name, permission level, server time, game version. |
| `GET /gm/api/health` | Skeleton health: Django responding, database readable. S2 folds this into `/gm/api/dashboard` and removes it. |

S1 adds only these endpoints. Data endpoints belong to later sub-projects.
Unknown `/gm/api/*` paths return the JSON error envelope with `404`, not the
SPA shell.

### Access control

- `web/gm/access.py` provides `gm_required`. Page views: unauthenticated →
  redirect to `LOGIN_URL?next=<path>`; insufficient permission → `403` page.
  API views: unauthenticated → `401` envelope (`code: "unauthenticated"`);
  insufficient permission → `403` envelope (`code: "forbidden"`).
- `web/gm/urls.py` registers views only through a `gm_path()` helper that
  applies `gm_required`. A contract test walks the URL resolver and fails if
  any pattern under `/gm/` resolves to a view not wrapped by `gm_required`.

### API conventions

- Success: `{"ok": true, "data": <payload>}`.
- Failure: `{"ok": false, "error": {"code": "<snake_case>", "message": "<zh-TW>"}}`
  with the matching HTTP status. Clients branch on `code` only.
- Pagination (defined now, first used by S3): `?cursor=<opaque>&limit=<n>`,
  response `data: {"items": [...], "next_cursor": <opaque|null>}`.
- Writes use `POST` only and require the Django CSRF token, read by the SPA
  from the `csrftoken` cookie and sent as `X-CSRFToken`. S1 wires and tests
  this path with no write endpoint yet; S4 prompt reload is the first consumer.
- No Django REST framework (Evennia's `REST_API_ENABLED` stays `False`). Plain
  Django views plus a small JSON helper in `web/gm/responses.py`.

### Observability

- Every GM API request emits `gm_request` (info) with `account`, `route`,
  `status` in `context`.
- Access denials emit `gm_denied` (warn) with `account` (or `anonymous`) and
  `route`.
- New modules adopt the facade from the start and never enter
  `tools/observability_freeze.json`.

### Tests

- `web/gm/tests/` using `EvenniaTest`: anonymous, ordinary player, Developer,
  and superuser against pages and both API endpoints; the `/gm/api/*` 404
  envelope; the URL-resolver access-coverage contract.
- New test modules are registered in `.github/evennia-shards.json` in the same
  change.

## 5. S1 frontend (`web/admin-app/`)

### Build

- A separate `vite.gm.config.js` and a `pnpm run build:gm` script output to
  `web/static/gm/dist/` with stable `index.js` and `index.css`. The existing
  `vite.config.js` asserts exactly one entry stylesheet, so the game build is
  left unchanged rather than gaining a second entry.
- `web/templates/gm/index.html` is the SPA shell referencing those stable
  names.
- The container image and CI build steps run `build:gm` alongside the game
  build; the `dist` output is always built from sources, never hand-authored.

### Shared design system boundary

- Allowed imports from the game tree: `web/webclient-app/styles/tokens.css`
  and `web/webclient-app/styles/fonts*.css` only. These provide the ink-night
  palette, paper text colours, seal-red and muted-gold accents, type ramps,
  spacing, motion, and the `.ui-btn`, `.ui-tabs`, `.status-marker` utilities.
- Forbidden: `app-shell.css` (game-specific `.elosern-root` overrides) and any
  `web/webclient-app/components/**` module (they assume `--ui-scale` and the
  AVG stage).
- A dependency-free Node test enforces the boundary by scanning
  `web/admin-app/` imports.
- The portal's own component set lives in `web/admin-app/components/`, built
  on tokens only: `GmShell`, `GmNav`, `GmPageHeader`, `GmPanel`, `GmTable`,
  `GmEmpty`, `GmError`, `GmStatusBadge` (wraps `.status-marker`).

### Layout

```
+----------+-------------------------------------------+
| ELOSERN  | Page title                 account · 登出  |
| GM       +-------------------------------------------+
|----------|                                           |
| 總覽      |   Content area (panels / tables)          |
| 維運      |                                           |
| 執行期狀態 |                                           |
| 世界資料   |                                           |
| 操作      |                                           |
| GM 介入   |                                           |
+----------+-------------------------------------------+
```

- The side navigation has one section per sub-project. Sections whose
  sub-project has not landed render disabled with the label 尚未開放; no
  placeholder pages.
- UI copy is Traditional Chinese. Data identifiers (registry keys, quest ids,
  record ids) render verbatim in the monospace face.
- `.ui-btn--danger` and seal-red are reserved for destructive or
  state-changing actions (S5/S6).

### State and routing

- `vue-router` (history mode, base `/gm/`) is added as a dependency; Pinia is
  already present.
- `web/admin-app/lib/api.js` is the single fetch boundary: attaches
  `X-CSRFToken` on writes, unwraps the envelope, redirects to login on `401`,
  routes to a 權限不足 view on `403`, and surfaces other errors by `code`.
- The S1 home view (總覽) renders `/gm/api/session` and `/gm/api/health`. S2
  replaces it with the dashboard.

### Tests

- Vitest: `lib/api.js` envelope and error branches (401, 403, 404, network
  failure, malformed body), router guards, `GmShell` navigation state
  including disabled sections.
- Storybook stories for every `Gm*` component, included in the showcase
  coverage gate.

## 6. Scope of S2–S6

### S2 Operations dashboard

Designed in `docs/superpowers/specs/2026-10-06-gm-portal-s2-dashboard-design.md`
and split into S2a (LLM transcript log and the repeal of the
no-prose-in-logs rule) and S2b (the dashboard, fed by an in-memory
recent-event buffer and the transcript). LLM health is passive, derived from
recent calls; no endpoint probes are sent.

### S3 Runtime state inspection

Designed in `docs/superpowers/specs/2026-10-06-gm-portal-s3-runtime-state-design.md`:
curated read-only entity views reusing the existing read models, a generic
raw-data tab for every Evennia object, cross-linked navigation, and a
read-only NPC recall preview.

### S4 Authored data browser

Designed in `docs/superpowers/specs/2026-10-06-gm-portal-s4-world-data-design.md`:
a hand-maintained registry index, reference declarations on dataclass fields
(`ref`/`ref_many` with named inverses) checked by a CI contract, entry pages
with references and referrers, cross-registry search, and a read-only source
viewer for rulebook and prompt YAML.

### S5 Save management

Designed in `docs/superpowers/specs/2026-10-06-gm-portal-s5-saves-design.md`.
Responsibility: save and restore the world state (database plus art store).
Operations a player can already perform in game (art requeue, persona
editing, time skip) are not portal features.

### S6 Save repair

- Granting items and currency (integer copper), correcting quest progress,
  flagging or retracting memory records, and similar interventions.
- Each capability first lands as a validated, all-or-nothing API in its
  owning single-writer package; the portal only calls it.
- Every intervention first creates an `auto_intervention` save through S5.
- A persistent GM audit record: operator, timestamp, target, before/after
  diff, stated reason.
- Decision deferred to S6: the package that owns the audit record. AGENTS.md
  requires every writing package to be named explicitly, so S6 amends
  AGENTS.md in the same change.

## 7. Error handling principles

- Offline external services are rendered as status, never as an error page;
  the portal remains usable.
- API errors always carry a stable `code` and a zh-TW `message`; the client
  branches on `code` only.
- Failed writes take no effect (the all-or-nothing semantics of the rule
  APIs), and the rule layer's rejection reason is shown verbatim.
