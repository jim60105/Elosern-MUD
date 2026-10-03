## Context

See proposal.md for motivation and batch prerequisites. The approved narrative design is authoritative for this boundary; existing main specs remain current until the owning delta is implemented/synced. The project is pre-release.

## Goals / Non-Goals

**Goals:** Deliver only this boundary using completed prerequisites; no empty future subsystem packages. Generation proposes only; narrative owns and applies only its persistent data. Other writes route through rules/quests/maps; lore/skills remain read-only.

**Non-Goals:** No cargo, vectors, general agent framework, compatibility layers, data migrations, or unrelated gameplay rewrites.

## Decisions

### 1. Boundary decision

Use deterministic Traditional Chinese tokenization, normalized entity matching and BM25 over access-filtered owners; no embeddings. Pin tokenizer versions/segmentation and source-ID ties. Owner/requested thread filters precede ranking; actual thread support waits for W3 linkage.

### 2. Boundary decision

Bound fixed core/working selection independently. Require lexical relevance before metadata bonuses rerank; salience alone cannot admit an unrelated episode. Return empty recall intentionally.

### 3. Boundary decision

Commit synthetic labels covering entity aliases/paraphrases, unrelated salient negatives, uninformed roles, supersession/history and ties. Measure Recall@1, Recall@2, false positives and latency with corpus/environment before committing numerical gates; do not invent universal limits.

### 4. Boundary decision

Use a replaceable in-process lexical index keyed by owner generation and tokenizer/ranker versions. Offline rebuilds preserve ordered results.

## Risks / Trade-offs

- Cross-owner mutation or generator authority creep → value-only generation and deterministic owner routing; test forbidden writes.
- Stale context or duplicate settlement → immutable source/version identities, revalidation at apply and transactional idempotency at the relevant boundary.
- Scope expansion → implement only the listed boundary; future behavior gets its own real proposal rather than a stub or compatibility path.

Main-spec reconciliation: No main-spec behavior conflict; additive capability.
