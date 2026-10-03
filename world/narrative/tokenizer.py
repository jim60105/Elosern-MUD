"""Deterministic Traditional Chinese tokenization and entity matching for narrative recall.

No external unpinned dependencies; uses Python stdlib unicode & regex.
Handles:
- Traditional Chinese character n-grams (unigrams and bigrams) and entity terms
- Traditional Chinese stopword filtering (stripping functional particles like 的, 了, 在, 是, etc.)
- Alphanumeric / English words (lowercased)
- Entity aliases / canonicalization
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Sequence

TOKENIZER_VERSION = "tc_v1"

# CJK Unified Ideographs and Extension blocks
CJK_PATTERN = re.compile(
    r"[\u4e00-\u9fff"  # CJK Unified Ideographs
    r"\u3400-\u4dbf"  # CJK Unified Ideographs Extension A
    r"\uf900-\ufaff]"  # CJK Compatibility Ideographs
)

# Alphanumeric words (English / Latin / digits)
WORD_PATTERN = re.compile(r"[a-zA-Z0-9_]+")

# Common Traditional Chinese functional particles / stopwords
TC_STOPWORDS: frozenset[str] = frozenset({
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一個", "上", "也", "很", "到", "說", "要", "去", "你", "會", "著",
    "沒有", "看", "好", "自己", "這", "那", "與", "及", "或", "之", "於",
    "以", "而", "等", "被", "把", "讓", "向", "從", "自", "往", "朝",
    "前", "後", "中", "裡", "外", "內", "間", "旁", "邊", "側",
    "個", "位", "隻", "條", "件", "張", "本", "顆", "首", "次",
    "嗎", "呢", "吧", "啊", "呀", "哦", "啦", "麼", "什麼", "怎麼",
    "那裡", "這裡", "哪裡", "這個", "那個", "哪個",
})

# Entity aliases mapping (variants / abbreviations to canonical forms)
# Maps Traditional Chinese, English, and structured tokens to canonical domain concepts
ENTITY_ALIAS_MAP: dict[str, str] = {
    # Yohanna
    "尤漢娜": "尤漢娜",
    "尤漢娜‧庫柏": "尤漢娜",
    "尤漢娜庫柏": "尤漢娜",
    "庫柏": "尤漢娜",
    "yohanna": "尤漢娜",
    "yohanna cooper": "尤漢娜",
    "cooper": "尤漢娜",
    # Courier
    "銀羽驛行": "銀羽驛行",
    "銀羽驛站": "銀羽驛行",
    "銀羽": "銀羽驛行",
    # Protection & Encounter
    "保護": "保護",
    "援護": "保護",
    "守護": "保護",
    "防衛": "保護",
    "protection": "保護",
    "protected": "保護",
    "protect": "保護",
    "遭遇": "遭遇",
    "戰鬥": "遭遇",
    "encounter": "遭遇",
    "combat": "遭遇",
    # Companions & Roles
    "隊友": "同行者",
    "同伴": "同行者",
    "companion": "同行者",
    "冒險者": "冒險者",
    "adventurer": "冒險者",
    "player": "玩家",
}


def normalize_text(text: str) -> str:
    """Normalize text into NFKC representation, lowercasing Latin characters."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text).lower()
    return normalized


def extract_entities(text: str) -> list[str]:
    """Extract recognized entity mentions and map aliases to canonical form."""
    norm = normalize_text(text)
    entities: list[str] = []
    # Sort aliases by length descending for greedy match
    sorted_aliases = sorted(ENTITY_ALIAS_MAP.keys(), key=len, reverse=True)
    matched_ranges: list[tuple[int, int]] = []

    for alias in sorted_aliases:
        alias_norm = normalize_text(alias)
        start = 0
        while True:
            idx = norm.find(alias_norm, start)
            if idx == -1:
                break
            end = idx + len(alias_norm)
            # Check overlap with already matched entities
            overlap = any(max(start1, idx) < min(end1, end) for start1, end1 in matched_ranges)
            if not overlap:
                canonical = ENTITY_ALIAS_MAP[alias]
                entities.append(canonical)
                matched_ranges.append((idx, end))
            start = idx + 1

    return entities


def tokenize(text: str) -> list[str]:
    """Tokenize Traditional Chinese and alphanumeric text deterministically.

    Emits:
    - Canonical entity tokens
    - CJK unigrams (non-stopwords) and bigrams
    - Latin/alphanumeric words (non-stopwords)
    """
    if not text:
        return []

    norm = normalize_text(text)
    tokens: list[str] = []

    # 1. Canonical entities
    entities = extract_entities(text)
    tokens.extend(entities)

    # 2. Extract CJK runs and Latin words
    current_cjk: list[str] = []

    for char in norm:
        if CJK_PATTERN.match(char):
            current_cjk.append(char)
        else:
            if current_cjk:
                cjk_str = "".join(current_cjk)
                # Unigrams (filter functional particles / stopwords)
                for ch in cjk_str:
                    if ch not in TC_STOPWORDS:
                        tokens.append(ch)
                # Bigrams (filter if both chars are stopwords or exact stopword)
                if len(cjk_str) > 1:
                    for i in range(len(cjk_str) - 1):
                        bg = cjk_str[i : i + 2]
                        if bg not in TC_STOPWORDS and not (bg[0] in TC_STOPWORDS and bg[1] in TC_STOPWORDS):
                            tokens.append(bg)
                current_cjk = []

    if current_cjk:
        cjk_str = "".join(current_cjk)
        for ch in cjk_str:
            if ch not in TC_STOPWORDS:
                tokens.append(ch)
        if len(cjk_str) > 1:
            for i in range(len(cjk_str) - 1):
                bg = cjk_str[i : i + 2]
                if bg not in TC_STOPWORDS and not (bg[0] in TC_STOPWORDS and bg[1] in TC_STOPWORDS):
                    tokens.append(bg)

    # 3. Alphanumeric words
    words = WORD_PATTERN.findall(norm)
    for w in words:
        if w not in TC_STOPWORDS:
            tokens.append(w)

    return tokens
