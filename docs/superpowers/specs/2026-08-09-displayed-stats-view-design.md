# Displayed-Stats View — Design

**Date:** 2026-08-09
**Status:** Approved
**Scope:** The third `disguised_stats` consumer (master design D2) as a direct player-facing view:
displayed combat values on `look <target>`.

This document is a slice of the master design
(`docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`, D2 and §5.2 amendment). It explicitly
amends the D2 consumer form: the forward-declared "appraisal items" consumer becomes a direct
view surface with no item or service.

---

## 1. Product Context

D2 fixes `disguised_stats` as a pure display layer with exactly three consumers: appearance
rendering (`look` / the status read model), guild-registration historical snapshots, and appraisal.
The first two are live; the third exists only as a forward-declared seam: `get_display_value()`'s
docstring (`world/rules/traits.py:192-202`, "appraisal items") and the boundary contract test
(`world/rules/tests/test_guild_registration.py:198`). The main `disguised-stats-boundary` spec
explicitly permits the deferral ("Appearance and appraisal MAY remain deferred").

This change claims the consumer in a new form decided by the owner: displayed stats become a
first-class system mechanic — the player reads any present target's displayed values directly from
`look <target>`, with no appraisal item and no NPC service.

---

## 2. Design Decisions

| # | Decision | Rationale |
|---|---|---|
| A1 | **The consumer is a `look <target>` stat block**, not an item or service. | Owner decision: displayed values are part of the system's surface, and viewing them is a free direct operation. |
| A2 | **Block keys are the combat five: `atk_phys`, `agility`, `defense`, `magic_level`, `hp`**, all read through `get_display_value()`. | Isomorphic to the combat preview surface; disguised keys return disguised values and non-disguised keys return true values (existing function behavior). Excludes `mp`/`sp`/`guild_merit`. |
| A3 | **Applies to every present living entity** (NPC, player, monster). | One uniform semantics: any look-able target carries the block; no observer-resolution exceptions. |
| A4 | **Telnet and WebClient share one renderer.** `look <target>` and `explore.look`'s target detail both render through the same function. | Presentation-layer consistency; the browser never recomputes values. |
| A5 | **The onboarding `at_look` seam is untouched.** | The block is appended only on the target-detail path; the guide's `look` detection is unaffected. |
| A6 | **The master design and main spec are amended.** §5.2's "appraisal items remain a forward-declared seam" is rewritten to name the `look <target>` block; `disguised-stats-boundary` receives the matching delta. | Documentation stays consistent with the implementation, per the project's amendment convention. |

---

## 3. System Design

### 3.1 Single renderer

`world/rules/status_query.py` (the look/status read model):

```python
def display_stat_block(entity) -> str | None:
    """Render the five displayed combat values for look <target>.

    Reads every key through get_display_value(); returns None for non-living
    targets so look appends nothing.
    """
```

- Fixed order: `atk_phys`, `agility`, `defense`, `magic_level`, `hp`, one `label：value` row each.
- Entities without a disguise still show the block (displayed values equal true values); non-living
  entities (objects, rooms) yield `None`.
- Pure read: never touches traits, never writes attributes.

### 3.2 look integration

- `look <target>` (localized path) appends the block after the target's description.
- `look` (the room) does not append the block.
- The block appears only for explicitly named targets.

### 3.3 WebClient parity

- `explore.look`'s target detail calls the same renderer; this change ships the block as text
  (structured panel fields are a future seam).

### 3.4 Contract update

- `get_display_value()`'s docstring and the `disguised-stats-boundary` spec rename the three
  consumers to "appearance rendering (`look`), guild registration records, and the `look <target>`
  displayed-stats block".
- The forbidden-caller surface is unchanged: combat, resolution, and damage never call it.

---

## 4. Integration Points

| Integration | Direction |
|---|---|
| `world/rules/status_query.py` | `display_stat_block()` renderer |
| `look <target>` command path | Appends the block |
| `web/webclient/actions/exploration_actions.py` | `explore.look` target detail appends the same block |
| `world/rules/traits.py` | Docstring contract updated |
| Onboarding | `at_look` detection unchanged (regression test) |

---

## 5. Error Handling and Degradation

| Situation | Behavior |
|---|---|
| Target is not a living entity | No block (`None`); `look` behaves as today |
| Missing or malformed trait | That row is omitted; the rest render; never raises |
| Malformed `disguised_stats` (non-dict) | `get_display_value()`'s existing behavior (true value); no new exception path |
| WebClient look failure | Existing presenter isolation; the text path is unaffected |

---

## 6. Testing Strategy

| Area | Method |
|---|---|
| Renderer | Pure `unittest.TestCase`: disguised entity (disguised keys return disguised values, others true), no-disguise entity, non-living target → `None`, fixed key order |
| look integration | `EvenniaTest`: Telnet `look <target>` carries the block; bare `look` does not; onboarding `at_look` regression stays green |
| explore.look | WebClient target detail carries the same block |
| Contract | `get_display_value` forbidden-caller tests; `disguised-stats-boundary` delta; design-doc amendment |
| Command docs | `docs/game/commands.md` / `command-reference.md` and `tests/test_command_docs.py` updated if the documented `look` output contract changes |

---

## 7. OpenSpec Slicing

One per-day change:

| # | Change | Depends on | Content |
|---|---|---|---|
| 1 | `displayed-stats-view` | 3 (`entity-traits`), 8 (`action-resolver`), 23d (`explore.look`) | Renderer, `look <target>` append, `explore.look` parity, contract and doc updates, tests |

If a smaller slice is ever needed, split Telnet `look` from WebClient `explore.look` parity; the
renderer is shared either way.

---

## 8. Out of Scope

- Appraisal items and appraiser services (explicitly dropped in favor of the direct view).
- Viewing true values or any see-through-disguise mechanism (forbidden by D2).
- A combat-time target stat panel (the combat surface already carries `context_actions`).
- Player-to-player stat comparison or rankings.

---

## 9. Open Questions Carried Forward

- None blocking. Whether the block later becomes structured WebClient panel fields, and whether a
  future item or service reuses the same renderer as a paid convenience, are deferred decisions;
  the renderer is the shared seam either way.
