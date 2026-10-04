# Narrative Memory & Fast Recall Developer Guide

## Overview

The `world/narrative` subsystem manages persistent narrative events, character memory cognition, and calibrated lexical recall.

### Core Modules

1. **`world/narrative/events.py`**:
   - Manages durable `NarrativeEvent` records with immutable provenance and idempotent projection tracking via `ProjectionProgress`.

2. **`world/narrative/memory.py`**:
   - Manages owner-scoped `MemoryRecord` and append-only `MemoryRevision` history.
   - Enforces knowledge scopes (`witnessed`, `told`, `inferred`, `public`) and owner privacy boundaries.
   - Increments `OwnerMemoryGeneration` on effective record changes.

3. **`world/narrative/tokenizer.py`**:
   - Deterministic Traditional Chinese and alphanumeric tokenizer (`tc_v1`).
   - Extracts canonical entity terms (e.g. `尤漢娜`, `銀羽驛行`, `保護`, `遭遇`).
   - Generates CJK unigrams and bigrams with Traditional Chinese stopword filtering.

4. **`world/narrative/ranker.py`**:
   - Pure-Python BM25 ranking (`bm25_v1`, $k_1=1.5, b=0.75$).
   - Precision-first lexical qualification threshold (`MIN_LEXICAL_THRESHOLD = 2.0`).
   - Requires substantive multi-character content overlap to prevent single common characters from admitting unrelated episodes.

5. **`world/narrative/recall.py`**:
   - `fast_recall(*, owner_id, query, requester_id=None, thread_id=None, limit=5, core_limit=3, working_limit=5, ...)`:
     - Step 1: Permission filtering and explicit scope checks (`get_owner_memories`, optional `thread_id` relation match).
     - Step 2: Bounded fixed memory selection (core and working tiers) ordered deterministically.
     - Step 3: BM25 lexical recall over qualifying candidates. Candidates scoring below the threshold are pruned; if none qualify, `recalled` is empty `[]`.
     - Step 4: Metadata bonuses (salience, confidence) rerank lexical candidates without ever rescuing non-lexical records.
     - Step 5: Replaceable tokenization cache keyed by owner generation.
     - Emits `narrative_fast_recall_executed` via `world.observability`.

6. **`world/narrative/calibration_runner.py` & `world/narrative/calibration_corpus.py`**:
   - Offline synthetic labeled fixtures and evaluation runner measuring Recall@1, Recall@2, false positive rate, and latency.
   - Committed report at `world/narrative/calibration_report.json`.

7. **`world/narrative/context.py`**:
   - Reproducible permission-filtered cognition context assembly with enforceable rendered budgets and immutable source snapshots.
   - Stable ordering: global rules, world digest, capability contract, character anchor, epoch summary, turn frames (recall items and affordances).
   - Budget profiles with completion reservation, future Deep Recall reservation, and estimation safety margins; selection and assembly share one rendered representation (headings included), and mandatory-section overflow rejects before generation.
   - Immutable `NarrativeContextSnapshot` model (append-only manager plus instance guards) tracking source IDs, read revisions, section hashes, budget accounting, truncation decisions, and the reconstructible rendered payload.
   - Thin `NarrativeRequestDescriptor` binding prompt messages, validators, and snapshot/trace identities, rejecting mismatched context/snapshot provenance.
   - Every fresh assembly reads the owner memory generation, so effective-memory changes surface to new generations while retries re-read the authoritative persisted snapshot instead of rewriting it.

## Durable face-to-face dialogue (W1)

`world.narrative.dialogue` replaces the destructive NPC Attribute history.
`submit_turn` allocates one ingress identity and preserves the original player
speech. `run_npc_exchange` carries that identity and the immutable snapshot ID
in its result; it never records an undelivered NPC response. Talk and both
invitation delivery callers record the displayed response through
`settle_response`, whose unique `(submission_id, kind)` key prevents duplicate
settlement. Authored offline greetings are delivered turns; silence and
stale-persona responses are not. Existing late co-location/schedule rejection
still displays validated speech but rejects its intent, so that displayed
speech remains in the archive.

`pair_view` reads only the configured tail (at most 12 turns), keyed by persistent
NPC/player identities. Trimming affects rendering only. Omitted-turn counts
accompany the prompt and snapshot; originals remain recoverable in
`DialogueTurn`. Changing a persona changes later rendering without rewriting
historical speech. There is no compatibility history store or migration of old
Attribute data.

Each exchange uses owner-permitted Fast Recall followed by the existing context
builder. Core and working selections remain fixed context. Protection events
project to the existing `archive` tier: durable episodic experience excluded from
fixed working selection, but eligible for relevant lexical recall. Unrelated
questions do not force that episode into cognition. The W1 system template stays
in the prompt library; cognition is added to the existing user JSON placement.
The snapshot captures the exact final system/user messages and only sources
whose recall block survived rendering. Normal logs contain IDs/counts, never
speech, private persona, or prompt prose.

## Author-controlled Yohanna protection/revisit route

The fresh NPC import card is `world/imports/examples/yohanna_cooper.json`.
It authors Yohanna Cooper's hereditary barrel-making family and guild artisan
connections, independently of temporary handoff plots. The compact-card importer
is the persona/age/name-validation boundary; `NPC_SOURCE_INVENTORY` records its
existing `import_example` ownership.

For an author-controlled local world, put an unbound player at a reachable room
on the guild approach, with no current fight. From the existing administrator
Python seam, call `world.rules.protection_demo.prepare_protection_demo(player)`.
For example, in an administrator's `@py` context where `self` is the player:

```python
from world.rules.protection_demo import prepare_protection_demo
npc, enemy = prepare_protection_demo(self)
```

This imports Yohanna beside the player, binds her through the real party owner,
and engages the lowest registry threat tier. It does not declare a victory.
Use the existing combat attack/action menu to defeat the creature while Yohanna
survives. Real combat settlement commits the protection fact; the normal
projection consumer creates her witnessed episode. Dismiss her with the existing
party-leave action so she stays at the encounter location. Use ordinary downtime
commands over several days, return to the same reachable room, and talk about
the earlier protection. An unrelated topic omits the recalled episode; the
pair's original dialogue can of course still mention it.

No new player command, alias, syntax, or availability context is introduced.
Permanent acceptance tests use a synthetic card and fixed combat rolls plus
`FakeLLMClient`; the separate registered authored-data contract checks the shipped
card and setup. A controlled recorded/offline smoke can run the focused
`DurableDialogueTests.test_real_protection_commit_multi_day_revisit_and_permissioned_recall`
and `test_offline_delivered_greeting_is_durable_but_silence_is_not` labels through
the guarded Evennia test entry point. Do not enable live model/image services for
automated checks or assert live wording. New delta-only requirement annotations
are added by the later spec-sync owner after obtaining their canonical main IDs;
this change annotates substantive tests against the existing main IDs.
