# Design: align-dialogue-budget-with-persona-cards

## Context

`build_dialogue_context` assembles a mandatory system message (global rules +
world digest + capability contract + character anchor carrying the NPC's
flattened persona card) and a mandatory current frame (player identity,
disguised stats, affinity, the player's public persona block) plus optional
replay frames, chat memory, recall cognition, and epoch summary. The
`token_est_v3` estimator charges 2 tokens per CJK code point, so the card
bound (2000 code points, `CARD_BLOCK_LIMIT`) and the player's public block
(field cap 600 + structural sections, block cap 2000) form a mandatory floor.
The profile previously used the generic `DEFAULT_PROFILE_CONTEXT_WINDOW` of
4096 (3078 after reservations) with `character_anchor` hard bound 1800;
measured live data (card 1905 est. tokens, system 2605, minimal user 671)
overflowed before any reduction step could apply.

## Goals / Non-Goals

- Goals: every valid persona-card pair converses without budget degradation;
  the sizing rule is contractualized; reduction order and reject-on-mandatory
  semantics stay intact.
- Non-Goals: provider-tokenizer accuracy, model-quality claims, transport
  window configuration, persona card bound changes.

## Decisions

1. **Window 16384, sized by content bounds not a provider window.**
   Worst-case mandatory floor: anchor ≈ card 4000 + framing/rules overhead
   (~600) ≈ 4600; current frame with a 2000-code-point public persona block
   plus a 12-line memory window of capped 200-code-point lines ≈ 11000.
   16384 (max input 15366 after 250+512+256 reservations) admits the worst
   case with headroom while staying conservative for local-first endpoints
   (`num_ctx` ≥ 16k is the Ollama-class norm). Alternative considered:
   shrinking the card injection (e.g. digesting the card) — rejected, the
   persona-dialogue-injection contract requires no truncation for a valid
   card.
2. **`character_anchor` hard bound 5200.** Covers the ~4600 worst-case anchor
   with margin; still well below max input, so the anchor cannot consume the
   whole budget (soft target 900 still drives normal sizing).
3. **`turn_frames` hard bound = max input (15366).** The mandatory current
   frame is serialized inside the user message that the post-assembly check
   measures as the `turn_frames` section. Any bound under
   `max_input - 0` can reject content the aggregate loop already admitted —
   the section check must not be tighter than the aggregate bound it
   post-dates. The reduction loop, not the section bound, governs optional
   history.
4. **Single aggregate bound.** Drop `min(system + section_bounds["turn_frames"],
   max_input)`: with the mandatory floor it could sink below system + current
   frame, a rejection no reduction can relieve. `budget.max_input_budget` is
   the sole aggregate cap; the loop's reduction ladder is unchanged.
5. **Keep estimator and reservations unchanged** (`token_est_v3`, 250/512/256):
   the failure was window sizing, not estimation.

## Risks / Trade-offs

- Larger prompts cost real tokens when providers bill by window usage: bounded
  by the same card/persona bounds that make the floor mandatory; optional
  history still trims oldest-first under the aggregate cap.
- Local endpoints with `num_ctx` < 16384 would truncate server-side: the
  estimator is conservative and typical shipped prompts sit near 3–6k tokens;
  deployment sizing stays an operator concern (profile knobs unchanged).
- Snapshot accounting `context_window` value changes 4096 → 16384: consumers
  read `max_input_budget`, and the de-pinned test now asserts the invariant.

## Migration Plan

Code-only change; no data migration (no released users). Rolling the container
image restarts dialogue with the new profile. Rollback = revert commit.

## Open Questions

(none)
