# Proposal: DA6 — defeat-aftermath-digest-narrative

Change ID: **DA6** (parent design §8 archive order).

## Why

After the violation sequence settles, everyone violated (player and
companions) wakes carrying whatever their own body recorded — that residue
is the point of the adult core and the honest place for consequences: each
person's own SexualState digest decides their wake-up condition and tone,
with zero affinity writes (being violated has no causal channel to how a
companion feels about the player) and zero race/species conditions (the
digest rulebook schema rejects them at load; persona is flavor-only per
design doc D7). This change lands the digest table, the digest buffs, the
tone-selected wake-up lines, the bystander wake observation, and the
Narrator prose overlay over the aftermath EventLog, completing the parent
design's §4.3.

## What Changes

- **Digest rulebook** (`rulebook/defeat_aftermath.yaml` digest section,
  section-owned validator): conditions read ONLY the violated entity's own
  existing fields — `sensitivity` level, `shame` level (end-of-sequence
  value; a Monster's permanently-pinned 無 shame simply never matches the
  humiliated band — no species key exists or is needed), end-of-sequence
  `arousal` ordinal — plus the sequence's in-memory `ViolationOutcome`
  (climax count, zero-landed flag) handed through the same settlement call;
  nothing is persisted for the digest. The section schema rejects any
  race/species/persona condition key at load. One of three outcomes:
  `residue` (positive-ish residual arousal buff), `humiliated` (negative
  mood buff), or `none` (pure dishevelment).
- **Digest buffs** (`rulebook/buffs.yaml` rows riding the shipped effect
  surface): `aftermath_residue` and `aftermath_humiliated`, world-second
  durations, `bounds`-surface modifiers.
- **Digest position in the phase order**: after the recovery advance,
  before the wake lines — wake at 5% first, then read what the body
  remembers.
- **Bystander wake observation** (distinct from a digest): a conscious
  allied bystander who was never selected receives no digest outcome and no
  buff — only a zh-tw observation line; `DigestOutcome` (selected
  participants only) and `WakeObservation` (bystanders) are separate
  outputs.
- **Wake-up lines**: wake templates are selected per entity by digest
  outcome; persona flavor text is passed to the Narrator overlay voice as
  flavor only — never a rulebook condition input or buff-grant input.
  Offline = deterministic template choice per digest.
- **Narrator overlay as a pure render function**: one prose paragraph per
  aftermath EventLog entry, in order, never rewriting or duplicating an
  already-rendered entry; failure/timeout/disabled discards only the
  overlay, leaving the deterministic template render byte-identical. The
  prompt library gains aftermath-kind guidance.

## Capabilities

### New Capabilities

- `defeat-aftermath-digest`: the own-body digest table (rulebook-validated,
  no species keys), digest buffs, digest-selected wake-up lines (persona as
  Narrator flavor only), the bystander wake observation, and the
  once-per-entry Narrator-overlay degradation contract.

### Modified Capabilities

_None — the Narrator's existing generic EventLog-to-prose mapping and its
template-fallback requirement already cover the aftermath entries; this
change registers templates and prompt guidance. The render contract
(one paragraph per entry, failure discards only the overlay) is specified
inside the new capability._

## Impact

- `world/rules/defeat_aftermath.py` (digest phase between the recovery
  advance and the wake lines; per-participant iteration),
  `world/rules/rulebook/defeat_aftermath.yaml` (digest rows + validator),
  `world/rules/rulebook/buffs.yaml` (two digest rows),
  `world/rules/player_messages.py` (wake template families per digest +
  bystander observation line), prompt library (`narrator.system` guidance
  for aftermath kinds).
- Tests: new `world/rules/tests/test_defeat_aftermath_digest.py` (digest
  bands, loader species-key rejection, bystander observation, render
  contract with disabled/failing/succeeding stubs); shard manifest updated
  same change.
- **Depends on**: `defeat-aftermath-violation-sequence` (the
  `ViolationOutcome` handoff) and `defeat-aftermath-companion-victims`
  (companion participants to digest); archives after
  `defeat-aftermath-recovery` per the parent design §8 order. No
  affinity-system contact.
