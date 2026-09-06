## Context

`world/rules/lore_knowledge.py` owns the codex: an eight-category registry mapping, an append-only
`db.lore_discovered` set, pure readers, and a card renderer. `commands/lore.py` surfaces it. The only
writer call site is the LLM `reveal_lore` dialogue intent.

Parent design: `docs/superpowers/specs/2026-09-06-quest-issuer-model-design.md` §7.

## Goals / Non-Goals

**Goals:**

- The codex fills through ordinary deterministic play.
- Reveals never interfere with the play that triggered them.
- The sole-writer contract is preserved exactly.

**Non-Goals:**

- No new codex category, card field, or registry.
- No change to the `lore` command or the non-disclosure rules.
- No player-facing "new codex entry" notification. Adding one is a separate UX decision; a toast on
  every room entry would be noise.

## Decisions

### D1: Reveal on arrival, not on knowing a destination exists

A quest can name an anchor the player has never visited. Revealing it at acceptance would put a place
in the codex the character has not seen, which contradicts the codex's "only what you discovered"
premise and the non-disclosure rule the `lore` command enforces. Arrival is the honest trigger.

### D2: Reuse the REACH resolution, not a second lookup

The room-arrival observation point already resolves a room against anchors and regions to match
`REACH` objectives. Reusing that resolution means the codex and the quest system can never disagree
about what room counts as which anchor.

### D3: Best-effort, and loud in the log rather than silent

`AGENTS.md` requires an `except` block to re-raise, emit a facade event with the exception, or carry
a reasoned exemption. Reveals take the middle option: the game continues, and the failure is fully
visible in the log with its traceback. Propagating instead would let a corrupt codex record make a
character unable to walk into a town.

### D4: Silent reveals

No message is sent. The alternative — a line on every discovery — fires during combat and during
movement, exactly where the narrative feed is busiest. The codex surface is where discoveries are
read.

## Risks / Trade-offs

- **Arrival reveals fire on every movement** → The writer's repeat-reveal path is a no-op, and the
  resolution is a registry lookup already performed for `REACH`, so the marginal cost is one set
  membership test per move.
- **Origin reveals depend on creation and registration commit paths** → Both are already
  transactional; the reveal runs after commit so it can never roll one back.
- **A player could infer registry contents from what appears** → No: entries appear only for places
  visited, tiers defeated, and origins chosen. Nothing undiscovered is disclosed, and the `lore`
  command's fixed not-found line is untouched.
