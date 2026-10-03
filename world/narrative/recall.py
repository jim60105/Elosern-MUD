"""Fast Recall retrieval service for narrative memory.

Provides deterministic, permission-filtered, calibrated Traditional Chinese
lexical recall combined with fixed core/working memory selection.
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass
from typing import Any, Optional, Sequence

from world.narrative.memory import (
    MemoryRecordView,
    get_owner_generation,
    get_owner_memories,
)
from world.narrative.ranker import (
    DEFAULT_B,
    DEFAULT_K1,
    MIN_LEXICAL_THRESHOLD,
    RANKER_VERSION,
    BM25Index,
    DocumentTokens,
)
from world.narrative.tokenizer import (
    TOKENIZER_VERSION,
    extract_entities,
    tokenize,
)
from world.observability import log_info

# In-process cache of raw tokenized records per owner
# Cache key: (owner_id, owner_generation, tokenizer_version) -> dict[int, DocumentTokens]
# Keep bounded to avoid unbounded historical memory growth
_OWNER_TOKEN_CACHE: dict[tuple[str, int, str], dict[int, DocumentTokens]] = {}
_MAX_CACHED_GENERATIONS_PER_OWNER = 2


@dataclass(frozen=True)
class ScoredMemory:
    """A memory view coupled with its retrieval scoring details."""

    view: MemoryRecordView
    lexical_score: float
    metadata_bonus: float
    final_score: float


@dataclass(frozen=True)
class FastRecallResult:
    """The structured result of a fast recall query."""

    owner_id: str
    generation: int
    tokenizer_version: str
    ranker_version: str
    query: str
    recalled: tuple[ScoredMemory, ...]
    core: tuple[MemoryRecordView, ...]
    working: tuple[MemoryRecordView, ...]

    @property
    def all_selected(self) -> tuple[MemoryRecordView, ...]:
        """Deduplicated, ordered selection combining fixed core, working, and recalled memories."""
        seen: set[int] = set()
        combined: list[MemoryRecordView] = []
        for v in (*self.core, *self.working, *(sm.view for sm in self.recalled)):
            if v.id not in seen:
                seen.add(v.id)
                combined.append(v)
        return tuple(combined)


def _tokenize_memory_view(view: MemoryRecordView) -> DocumentTokens:
    """Extract and tokenize searchable text fields from a MemoryRecordView."""
    # 1. Content prose / fields
    content_parts: list[str] = []
    if isinstance(view.content, dict):
        for k, val in view.content.items():
            if isinstance(val, str):
                content_parts.append(val)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, str):
                        content_parts.append(item)
    elif isinstance(view.content, str):
        content_parts.append(view.content)

    content_text = " ".join(content_parts)
    content_tokens = tuple(tokenize(content_text))

    # 2. Subjects
    subject_tokens: list[str] = []
    for s in view.subjects:
        if isinstance(s, str):
            subject_tokens.extend(tokenize(s))
    subject_tokens_tuple = tuple(subject_tokens)

    # 3. Category
    cat_tokens = tuple(tokenize(str(view.category)))

    # Combined full tokens
    all_tokens = tuple((*content_tokens, *subject_tokens_tuple, *cat_tokens))

    return DocumentTokens(
        doc_id=view.id,
        tokens=all_tokens,
        content_tokens=content_tokens,
        subject_tokens=subject_tokens_tuple,
        category_tokens=cat_tokens,
    )


def _get_tokenized_view(
    view: MemoryRecordView,
    generation: int,
    tokenizer_version: str,
) -> DocumentTokens:
    """Retrieve tokenized document from cache or compute it."""
    cache_key = (view.owner_id, generation, tokenizer_version)
    owner_cache = _OWNER_TOKEN_CACHE.get(cache_key)
    if owner_cache is None:
        # Prune old generations for this owner if cache exceeds bound
        owner_keys = [k for k in _OWNER_TOKEN_CACHE.keys() if k[0] == view.owner_id and k[2] == tokenizer_version]
        if len(owner_keys) >= _MAX_CACHED_GENERATIONS_PER_OWNER:
            owner_keys.sort(key=lambda k: k[1])  # sort by generation ascending
            for old_key in owner_keys[: len(owner_keys) - _MAX_CACHED_GENERATIONS_PER_OWNER + 1]:
                _OWNER_TOKEN_CACHE.pop(old_key, None)

        owner_cache = {}
        _OWNER_TOKEN_CACHE[cache_key] = owner_cache

    if view.id in owner_cache:
        return owner_cache[view.id]

    doc_tokens = _tokenize_memory_view(view)
    owner_cache[view.id] = doc_tokens
    return doc_tokens


def fast_recall(
    *,
    owner_id: str,
    query: str,
    requester_id: Optional[str] = None,
    thread_id: Optional[str] = None,
    limit: int = 5,
    core_limit: int = 3,
    working_limit: int = 5,
    include_superseded: bool = False,
    include_inactive: bool = False,
    min_threshold: float = MIN_LEXICAL_THRESHOLD,
    k1: float = DEFAULT_K1,
    b: float = DEFAULT_B,
) -> FastRecallResult:
    """Execute deterministic Fast Recall with permission filtering and fixed selections.

    Invariants:
    1. Permission & explicit scope filter FIRST:
       - Uses `get_owner_memories` to enforce knowledge scopes and ownership.
       - If thread_id is requested, filters records whose relations['thread_id'] matches.
    2. Fixed core & working memory selection:
       - Selected independently of lexical relevance up to core_limit and working_limit.
       - Deterministically ordered by (-salience, -tick, source_id, id).
    3. Precision-first BM25 lexical recall:
       - Query tokens extracted using Traditional Chinese tokenizer.
       - Lexical candidates must score >= min_threshold to qualify.
       - If no candidate qualifies, recalled result is strictly EMPTY [].
       - Metadata bonuses (salience / recency) ONLY rerank qualifying candidates.
    4. Deterministic tie breaking:
       - Candidates sorted by (-final_score, -lexical_score, -salience, -tick, source_id, id).
    5. Replaceable in-process tokenization cache keyed by owner generation.
    """
    start_time = time.monotonic()
    clean_owner = str(owner_id).strip()
    generation = get_owner_generation(clean_owner)

    # 1. Step: Permissions and explicit scope filtering
    all_views = get_owner_memories(
        owner_id=clean_owner,
        requester_id=requester_id,
        include_superseded=include_superseded,
        include_inactive=include_inactive,
    )

    # If thread_id is explicitly requested, filter by relations['thread_id']
    if thread_id is not None:
        clean_thread = str(thread_id).strip()
        filtered_views = []
        for v in all_views:
            rel_thread = v.relations.get("thread_id")
            if rel_thread is not None and str(rel_thread).strip() == clean_thread:
                filtered_views.append(v)
        eligible_views = filtered_views
    else:
        eligible_views = all_views

    # 2. Step: Bounded Fixed Selection (core & working)
    core_candidates = [v for v in eligible_views if v.tier == "core"]
    working_candidates = [v for v in eligible_views if v.tier == "working"]

    def _fixed_sort_key(v: MemoryRecordView) -> tuple[int, int, str, int]:
        return (-v.salience, -v.tick, v.source_id, v.id)

    core_candidates.sort(key=_fixed_sort_key)
    working_candidates.sort(key=_fixed_sort_key)

    selected_core = tuple(core_candidates[: max(0, core_limit)])
    selected_working = tuple(working_candidates[: max(0, working_limit)])

    # 3. Step: BM25 Lexical Recall over eligible views
    clean_query = str(query).strip() if query else ""
    query_tokens = tokenize(clean_query)
    query_entities = set(extract_entities(clean_query))

    recalled_scored: list[ScoredMemory] = []

    if query_tokens and eligible_views and limit > 0:
        # Build tokenized docs for eligible views keyed by record id
        tokenized_docs = [
            _get_tokenized_view(v, generation, TOKENIZER_VERSION)
            for v in eligible_views
        ]
        index = BM25Index(tokenized_docs, k1=k1, b=b)

        query_tf = Counter(query_tokens)
        query_content_terms = set(query_tokens)

        # Score candidates
        scored_candidates: list[ScoredMemory] = []
        for view, doc in zip(eligible_views, tokenized_docs):
            lex_score = index.score_doc(doc, query_tf, query_content_terms)

            # Precision-first gate: candidate must pass lexical threshold
            if lex_score < min_threshold:
                continue

            # Metadata bonus: only reranks candidates that passed lexical threshold
            # Bonus derived from salience (0.0 to 1.0) and confidence
            salience_bonus = min(1.0, max(0.0, view.salience / 100.0))
            meta_bonus = salience_bonus * float(view.confidence)
            final_score = lex_score + meta_bonus

            scored_candidates.append(
                ScoredMemory(
                    view=view,
                    lexical_score=lex_score,
                    metadata_bonus=meta_bonus,
                    final_score=final_score,
                )
            )

        # Deterministic sorting
        # (-final_score, -lexical_score, -salience, -tick, source_id, id)
        scored_candidates.sort(
            key=lambda sm: (
                -sm.final_score,
                -sm.lexical_score,
                -sm.view.salience,
                -sm.view.tick,
                sm.view.source_id,
                sm.view.id,
            )
        )
        recalled_scored = scored_candidates[: max(0, limit)]

    elapsed_ms = (time.monotonic() - start_time) * 1000.0

    # Observability facade logging
    log_info(
        "narrative_fast_recall_executed",
        context={
            "owner_id": clean_owner,
            "generation": generation,
            "query_length": len(clean_query),
            "recalled_count": len(recalled_scored),
            "core_count": len(selected_core),
            "working_count": len(selected_working),
            "duration_ms": round(elapsed_ms, 3),
        },
    )

    return FastRecallResult(
        owner_id=clean_owner,
        generation=generation,
        tokenizer_version=TOKENIZER_VERSION,
        ranker_version=RANKER_VERSION,
        query=clean_query,
        recalled=tuple(recalled_scored),
        core=selected_core,
        working=selected_working,
    )
