"""BM25 ranking and deterministic lexical scoring for narrative memories."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

RANKER_VERSION = "bm25_v1"

# Standard BM25 hyperparameters
DEFAULT_K1 = 1.5
DEFAULT_B = 0.75

# Precision-first qualification threshold: candidate must achieve a lexical score >= threshold
# Requiring meaningful multigram or multi-token overlap so a single trivial common character match
# cannot qualify an unrelated document.
MIN_LEXICAL_THRESHOLD = 0.25


@dataclass(frozen=True)
class DocumentTokens:
    doc_id: int
    tokens: tuple[str, ...]
    content_tokens: tuple[str, ...]
    subject_tokens: tuple[str, ...]
    category_tokens: tuple[str, ...]


class BM25Index:
    """In-memory BM25 index over a specific set of tokenized documents."""

    def __init__(
        self,
        docs: Sequence[DocumentTokens],
        k1: float = DEFAULT_K1,
        b: float = DEFAULT_B,
    ) -> None:
        self.k1 = k1
        self.b = b
        self.doc_count = len(docs)
        self.docs = docs
        self.doc_lens: dict[int, int] = {}
        self.doc_term_freqs: dict[int, Counter[str]] = {}
        self.doc_content_terms: dict[int, set[str]] = {}
        self.df: Counter[str] = Counter()

        total_len = 0
        for doc in docs:
            dlen = len(doc.tokens)
            self.doc_lens[doc.doc_id] = dlen
            total_len += dlen

            tf = Counter(doc.tokens)
            self.doc_term_freqs[doc.doc_id] = tf
            self.doc_content_terms[doc.doc_id] = set(doc.content_tokens)

            for term in tf.keys():
                self.df[term] += 1

        self.avg_doc_len = (total_len / self.doc_count) if self.doc_count > 0 else 0.0

    def idf(self, term: str) -> float:
        """Calculate Lucene-style / BM25 IDF: ln(1 + (N - n + 0.5) / (n + 0.5))."""
        n = self.df.get(term, 0)
        if n == 0:
            return 0.0
        val = math.log(1.0 + (self.doc_count - n + 0.5) / (n + 0.5))
        return max(0.0, val)

    def score_doc(
        self,
        doc: DocumentTokens,
        query_terms: Counter[str],
        query_content_terms: set[str],
    ) -> float:
        """Compute BM25 score for a single document against query terms.

        Requires substantive content overlap: matching only generic category/subject
        tokens without any content match yields 0.0 to prevent metadata leakage.
        Furthermore, at least one substantive multi-character term (length >= 2)
        must match in content to meet precision-first standards for CJK text.
        """
        doc_id = doc.doc_id
        doc_len = self.doc_lens.get(doc_id, 0)
        tf_map = self.doc_term_freqs.get(doc_id, Counter())
        doc_content_terms = self.doc_content_terms.get(doc_id, set())

        matching_content_terms = query_content_terms & doc_content_terms
        if not matching_content_terms:
            return 0.0

        # Substantive qualification check:
        # Require at least one multi-character term (entity, bigram, word >= 2 chars)
        # to match in content. Mere shared single characters (like '行' in '旅行' vs '運行',
        # or '術' in '劍術' vs '占星術') do not establish topical relevance.
        has_multichar_match = any(len(t) >= 2 for t in matching_content_terms)
        if not has_multichar_match:
            return 0.0

        score = 0.0
        for term, qf in query_terms.items():
            f = tf_map.get(term, 0)
            if f == 0:
                continue
            idf_val = self.idf(term)
            if idf_val <= 0.0:
                continue

            denom = f + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len if self.avg_doc_len > 0 else 1.0))
            term_score = idf_val * (f * (self.k1 + 1.0) / denom)
            score += term_score

        return score
