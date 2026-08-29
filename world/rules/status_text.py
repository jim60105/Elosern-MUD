"""Text-client breakdown renderer (expose-stat-breakdown-read-model D5).

Renders the SAME single ``CharacterReadModel`` assembly the character panel
serializes: one ``label：value（來源 ＋8｜來源 ×1.1｜來源 −10%）`` row per
panel stat, in the fixed panel order, with signed layer segments spelled
out in 正體中文 and the U+2212 minus convention shared with the P3
adjustment formatter. Purely presentational: it computes nothing, mutates
nothing, and the compact in-combat status surface keeps serializing
totals-only from the read model untouched.
"""

from typing import Any

from world.rules.status_query import TRAIT_LABELS

# The gauge rows carry a persisted remainder plus an effective maximum
# (``current／effective``); the remaining panel stats report one total value.
GAUGE_KEYS = ("hp", "mp", "sp")


def _number_text(value: int | float) -> str:
    """Render a read-model value; an integer-looking float prints bare."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return format(value, "g")


def _segment_text(layer: Any) -> str:
    """One ``來源 ＋8`` / ``來源 ×1.1`` / ``來源 −10%`` segment.

    ``mult`` amounts are factors (no sign prefix — a factor below one is
    self-describing); ``flat`` and ``pct`` amounts carry ＋/− (U+2212 for
    negatives), matching the P3 equipment adjustment prose.
    """
    if layer.kind == "mult":
        return f"{layer.name} ×{_number_text(layer.amount)}"
    magnitude = _number_text(abs(layer.amount))
    suffix = "%" if layer.kind == "pct" else ""
    sign = "＋" if layer.amount > 0 else "−"
    return f"{layer.name} {sign}{magnitude}{suffix}"


def _row_text(row: Any) -> str:
    """One breakdown row rendered as one 正體中文 text line."""
    label = TRAIT_LABELS.get(row.key, row.key)
    if row.key in GAUGE_KEYS:
        head = f"{label}：{_number_text(row.current)}／{_number_text(row.effective)}"
    else:
        head = f"{label}：{_number_text(row.current)}"
    if not row.layers:
        return head
    return f"{head}（{'｜'.join(_segment_text(layer) for layer in row.layers)}）"


def breakdown_text(model: Any) -> str:
    """Render every breakdown row of a character read model, in order."""
    return "\n".join(_row_text(row) for row in model.breakdown)


__all__ = ["GAUGE_KEYS", "breakdown_text"]
