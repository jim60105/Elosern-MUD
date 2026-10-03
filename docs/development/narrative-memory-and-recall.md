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
