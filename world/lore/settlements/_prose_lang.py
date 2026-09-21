"""Shared Traditional-Chinese prose check for authored room text (zhtw-room-prose).

The rule lives on ``grid-room-sync``: every authored room description the game
ships is Traditional Chinese prose, and a room's name and description are in
the same language. The check is deliberately a heuristic over the text rather
than a translation-quality judgement (design: "The guard checks prose, not
characters"): "contains a CJK character" would pass on exactly the shipped
defect this rule exists to prevent — a Chinese room name over an English body.

Two conditions make a description pass:

1. It is predominantly Han. The shipped corpus carries zero ASCII letter
   runs, and the old English corpus carried zero Han characters, so a Han
   character-count majority separates the two states with enormous margin.
2. It contains no run of five consecutive Latin-letter words — long enough
   to be a sentence, short enough that an author leaking a clause into an
   otherwise Chinese room still trips it. The threshold was tuned against
   the converted corpus, not before it (tasks 3.3): the shipped prose needs
   zero such tolerance today, and five is the shortest run that could still
   plausibly be a kept proper noun rather than prose. The check is on run
   length rather than on any Latin character precisely so a future
   description may name a command or keep a Latin-script term (design
   "Risks").
"""

import re

__all__ = ("english_prose_defects",)

# Five consecutive Latin-letter words read as a sentence to any reader.
_MAX_LATIN_WORD_RUN = 5

# A Latin-letter word (apostrophes/hyphens kept inside the word), then four
# more separated only by whitespace or punctuation — never another script's
# letters, which is what keeps a Chinese room citing a short Latin term safe.
_LATIN_WORD_RUN = re.compile(
    r"[A-Za-z]+(?:['’-]*[A-Za-z]+)*"
    r"(?:[’'”\"」』）)】】,、;；:：!！?？.…\s]+"
    r"[A-Za-z]+(?:['’-]*[A-Za-z]+)*){4}"
)


def _is_han(char: str) -> bool:
    """True for the CJK Unified Ideographs block (the prose's script range)."""
    return "\u4e00" <= char <= "\u9fff"


def _han_majority(desc: str) -> bool:
    han = sum(1 for char in desc if _is_han(char))
    latin_letters = sum(1 for char in desc if char.isascii() and char.isalpha())
    return han > 0 and han > latin_letters


def english_prose_defects(name: str, desc: str) -> list[str]:
    """Return the Traditional-Chinese-prose defects of one authored room.

    ``name`` is the room's key/name for the failure message; ``desc`` is its
    authored description. An empty list means the description is Han prose
    with no sentence-length English run.
    """
    if not desc or not desc.strip():
        return [f"{name}: authored room description is empty"]
    defects: list[str] = []
    if not _han_majority(desc):
        defects.append(
            f"{name}: description is not predominantly Han prose "
            "(Traditional Chinese)"
        )
    run = _LATIN_WORD_RUN.search(desc)
    if run:
        defects.append(
            f"{name}: description carries a {_MAX_LATIN_WORD_RUN}-word English "
            f"run: {run.group(0)!r}"
        )
    return defects
