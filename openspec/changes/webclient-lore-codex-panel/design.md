## Context

The codex backend is complete and unexposed. `LoreDrawer.vue` carries the codex name but renders
guild quest prose from the `services` payload.

Parent design: `docs/superpowers/specs/2026-09-06-quest-issuer-model-design.md` §8.2.

## Goals / Non-Goals

**Goals:**

- One payload the client can navigate two levels deep with no round trip.
- Non-disclosure so absolute that registry size is unlearnable from the wire.
- Bounds that fail loudly if the lore registries grow.

**Non-Goals:**

- No new OOB action — the codex is pure read.
- No client component (owned by `webclient-lore-codex-drawer`).
- No change to the codex backend, the category mapping, or the `lore` command's rules.

## Decisions

### D1: The whole codex in one payload

The eight registries hold a few dozen short entries in total, so the full listing plus every rendered
card sits far under the 65 536-byte envelope. Shipping it whole means the client does category and
entry navigation locally with no fetch action, no loading state, and no second protocol surface.

The bound is stable because the registries are immutable module-level data and the generative
pipeline never extends them.

### D2: Always all eight categories, even when empty

Shipping only non-empty groups would let a client infer, from a group's absence, that the player has
discovered nothing there — harmless — but would also make the client's category strip flicker as
groups appear. More importantly, a fixed eight-group shape makes the validator's "exactly eight, in
mapping order" check possible, which is a strong guard against a presenter bug reordering or dropping
a category.

Empty groups carry only key, label, `count` 0, and `[]`. They disclose nothing about what could be
there.

### D3: Fail closed on growth rather than paginate

If someone adds a hundred anchors, the right outcome is a failing test that forces a deliberate
decision about pagination — not a codex that silently stops showing the last entries. The envelope
guard and the explicit per-category and total caps make growth loud.

### D4: Category labels are shared, not duplicated

`commands/lore.py` already owns `CATEGORY_LABELS`. Promoting it to a shared location rather than
copying it means the text command and the panel can never disagree about what a category is called.

## Risks / Trade-offs

- **A discovered entry whose registry key vanished** → Omitted rather than shipped with a fabricated
  card, and the panel stays available. The stored record is not repaired, matching the reader's
  existing "never reset or fabricate" rule.
- **Full payload on every push** → Acceptable at this size; the push fires only on a genuinely new
  reveal, which is rare.
- **Bounds must be chosen now** → Set from current registry sizes with headroom, and pinned by a test
  that fails if a registry outgrows them, so the choice is revisited deliberately.
