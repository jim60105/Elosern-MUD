# Browser-First WebClient Suite — Worker Handoff

**Date:** 2026-08-02
**Status:** Design approved; implementation planning not started

## 1. Start Here

Read these sources before planning or proposing an OpenSpec change:

1. `AGENTS.md`
2. `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`
3. `docs/superpowers/specs/2026-08-02-webclient-ui-design.md`
4. The five focused WebClient designs linked from section 14 of the suite design

The suite design and focused designs are approved. Do not reopen browser-vs-Mudlet, visual style,
desktop scope, or text-vs-menu decisions unless the owner explicitly asks to amend them.

## 2. Repository State at Handoff

- Design commit: `cbf33e4 docs: design browser-first WebClient suite`
- Sequencing amendment: `16dc4e2 docs: clarify AI and WebClient sequencing`
- `openspec list --json` returned no active changes during design.
- `openspec validate --all --strict` passed with 75 specifications.
- No implementation code or dependencies were changed.
- No code test suite was run because this session changed documentation only.
- The worktree was clean after the sequencing commit.

The browser mockups under `.superpowers/` are ignored and are not source-of-truth artifacts. The written
designs contain every approved observable decision.

## 3. Required Next Step

Invoke the `writing-plans` skill and create an implementation plan for
`webclient-oob-foundation` only. Do not create one implementation plan for the entire UI suite. After the
plan is reviewed, use the repository's OpenSpec proposal/apply workflow for that delivery unit.

`llm-client` may be planned and implemented by a separate parallel worker. The first dependency wave is:

```text
17 llm-client                    23a webclient-oob-foundation
      │                                      │
      ├─ 18 narrator                         ├─ 23b combat menu
      ├─ 19 npc-dialogue                     ├─ 23c map knowledge
      └─ 20 scenario-director                ├─ 23e service menus
             │                               └─ 23g creation UI
             └─ 21 scene-builder
                    │
                    └─ 22 art-assets ──────────── 23f art panel

19 npc-dialogue ─┐
23c map knowledge ┴─ 23d exploration menu
```

Narrator does not block UI work because deterministic EventLog templates remain mandatory.

## 4. Contracts That Must Not Be Lost

### OOB ordering and reconnect

Every presentation message belongs to a server-generated `presentation_epoch`. Revisions are monotonic
only within one epoch. A valid full snapshot on a new transport atomically adopts its epoch and resets
revision comparison; delayed packets from prior epochs are discarded. Actions carry both epoch and base
revision.

This rule was added after independent review found that revision-only reconnect would reject a new
connection's lower revision.

### Presentation and mutation boundary

Presenters are read-only. `ui_action` accepts only allowlisted action IDs with exact bounded schemas.
Adapters obtain the actor from the authenticated session, re-resolve every referenced ID, and call public
deterministic APIs. They never write `.db`, traits, map records, or quest records directly. Narrative prose
is never parsed to infer UI state.

### Portrait focus

Keyboard focus remains client-local. The server art payload supplies a bounded `portrait_catalog` for
currently focusable present entities. Menu descriptors reference catalog entries, and the browser switches
only among those verified values. Do not add a focus mutation/input message or let the browser construct
portrait keys and URLs.

### Art enqueue authority

`world/art/service.py` is the only art queue writer. Startup synchronization, successful room entry, and
post-commit character/import/named-NPC lifecycle hooks ensure subjects idempotently. Presenters and workers
never enqueue while rendering. Queue failures do not roll back gameplay.

Generated assets use gitignored `server/.art/`, mounted at `/app/server/.art`. The `art-assets` change must
replace the current compose mount at `/app/world/art`, which would hide the future importable
`world/art/` Python package.

### Adult portrait gate

Both `age >= 18` and `apparent_age >= 18` are checked before portrait enqueue. Missing, malformed, or
underage records create no job or prompt. This is in addition to creation/import validation.

### Combat targets and Telnet parity

The combat-session facade must accept a target list or approved shorthand. NONE and SELF send no target
field; SELF binds the session puppet server-side. SINGLE sends exactly one target ID. AREA sends either a
nonempty target-ID list or one mutually exclusive shorthand.

Telnet receives stable session tokens (`a1`, `e1`, and so on) and exact forms such as
`cast wind_blade=e1,e2`. Existing single-target name search remains. The WebClient receives no exclusive
rule capability.

### Map amendment

Instance rooms and ordinary interiors receive only a coordinate-free local Exit graph. They gain no
xyzgrid/wilderness coordinate, world-map membership, pathfinding, auto-travel, nested instance, or
multi-room instance support. One-hop unvisited destinations are labelled `未探索`; their canonical room
details remain hidden until arrival.

### Required frontend gates

`webclient-oob-foundation` owns adding locked dev Playwright, Node unit tests, a managed isolated Evennia
browser harness, Chromium installation, and required quality-gate workflow steps. Browser checks are not
optional local tests.

