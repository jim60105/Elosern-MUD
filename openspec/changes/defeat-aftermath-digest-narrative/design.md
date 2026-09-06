# Design: defeat-aftermath-digest-narrative

Parent design: `docs/superpowers/specs/2026-09-06-defeat-aftermath-design.md`
§4.3 (companion two-layer model, own-state digest), §4.2 (Narrator overlay),
§3.2 item 3.

## Context

The violation sequence (`defeat-aftermath-violation-sequence`) writes
per-attempt state deltas through the existing sexual-state path. At the end
of the aftermath every violated entity's SexualState carries an observable
trail: end `arousal` ordinal, `climax_today`/lifetime counters, sensitivity
baseline, and — for entities whose shame is not pinned (companions; a
Monster's is permanently 無) — a real `shame` level. The core's wake step
currently emits one fixed template line. The sequence returns in-memory
`ViolationOutcome` objects per participant (companion-victims widens it to
a mapping); `roll_d100` is a stateless dice wrapper and the session record
persists no RNG cursor, so the digest must take its sequence-derived
signals from that handoff, not from stored replay state.

## Goals / Non-Goals

**Goals:**

- Own-body digest: conditions over existing fields select `residue` /
  `humiliated` / `none`; buffs ride the shipped `bounds` effect surface.
- Wake-line selection by digest; persona is flavor-only.
- Narrator overlay over aftermath EventLog with guaranteed template
  degradation.

**Non-Goals:**

- No affinity writes of any kind (owner decision — the removed "layer 2").
- No race/species/persona condition keys anywhere in the digest rulebook
  schema (design D7: persona never enters rules; the loader rejects them).
- No new EventLog kinds or narrator-layer transport requirements (the
  generic mapping already covers arbitrary entries).

## Decisions

**D-D1: Digest reads terminal observations plus the in-memory outcome handoff.**
Conditions are terminal observations (arousal ordinal, sensitivity level,
shame band) over the entity's own SexualState, plus the sequence's returned
`ViolationOutcome` (climax count, zero-landed flag) for that participant —
handed through the same settlement call, never persisted, so a replayed
settlement re-derives identical inputs from state-derived dice. One pass per
violated entity, deterministic, replay-safe. The digest persists nothing of
its own beyond its declared buff grants and EventLog line.

**D-D2: Three bands, table-ordered first-match.**
Rows evaluate in rulebook order: high sensitivity + climax ≥ 1 ⇒ `residue`;
low sensitivity + high shame ⇒ `humiliated`; else `none`. The bands are
explicit ordinal thresholds in YAML; the section validator rejects any
race/species/persona condition key at load. `shame` simply has no
qualifying band for Monsters (pinned 無), so monster digests always land
`residue`/`none` by construction, not by a Monster check.

**D-D3: Buffs are the mechanical face; lines are the cosmetic face.**
Digest outcome selects both a buff row (optional, `none` has none) and a
wake-line family; offline template selection uses the digest key directly,
so LLM-offline play has identical mechanics and only plainer prose.

**D-D4: Persona enters at wake rendering only.**
`persona.to_prompt_block()` may accompany the Narrator overlay for the
companion's line voice (existing narrator input discipline: keys/plain
data, bounded). It is not a digest condition input anywhere.

**D-D5: Overlay ordering.**
The Narrator overlay is a pure render function over the aftermath entries:
exactly one prose paragraph per entry in entry order, appended after the
fixed wake lines, never rewriting or duplicating an already-rendered entry.
A failure, timeout, or disabled profile discards the overlay wholesale —
the deterministic wake/template render stands byte-identical to the no-LLM
run. Three stub profiles (disabled / failing / succeeding) pin this. The
sequence stays fully playable with LLMs off (guardrail test).

**D-D6: Phase position — digest after the recovery advance.**
Order: violation sequence → departure → weak buff → recovery advance (wake
at 5%) → digest → digest buffs → wake lines → Narrator overlay. The body
wakes at its settled HP first; the digest then reads what it remembers.

**D-D7: Bystanders observe, they do not digest.**
`DigestOutcome` rows exist only for selected participants; a conscious
unselected bystander gets a `WakeObservation` line — no digest row, no
buff. The two shapes are separate types, so "bystander digest" is
unrepresentable.

## Risks / Trade-offs

- [Digest reads could double-count mid-fight arousal as "residue"] → Bands
  use end-of-sequence *deltas recorded by the sequence itself* for the
  climax/resist terms; the arousal/sensitivity terms are terminal
  observations. Pinned by a no-sequence test (core-only defeat ⇒ digest
  `none` or PG band only).
- [`shame` band silently never matches Monsters] → intentional (their shame
  is pinned); a test asserts a Monster digest lands `residue`/`none`
  without ever consulting species.
- [Persona flavor leaking into rules] → reviewer checklist item; digest
  loader validates condition keys against a closed field vocabulary.
