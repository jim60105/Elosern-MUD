"""Generate the one-cell code point table of the map's monospace cell measure.

The map geometry budgets label text in monospace cells (design D1,
webclient-map-label-cell-budget): a code point the bundled monospace face
draws one cell wide counts as one cell, every other code point as two. The
one-cell set is the face's own regular-weight code point manifest, committed
next to its slices, so the table needs no Unicode-version agreement with the
font build.

This pure generator collapses that manifest into sorted inclusive runs and
rewrites the ``CELL_EM`` line and the block between ``// BEGIN GENERATED
one-cell`` and ``// END GENERATED one-cell`` in
``web/webclient-app/lib/mono_cells.js``.
``tests/test_mono_cells_table.py`` rebuilds the block in memory and
byte-compares it, so the committed table can never drift from the manifest.

Run: ``uv run --locked python tools/gen_mono_cells.py``
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
# The bundled monospace face's slice manifest; a font change repoints this.
MANIFEST_PATH = REPO_ROOT / "web/webclient-app/fonts/jimmonotc/codepoints.json"
MANIFEST_KEY = "regular"
OUTPUT_PATH = REPO_ROOT / "web/webclient-app/lib/mono_cells.js"

CELL_MARKER = "// BEGIN GENERATED CELL_EM"
CELL_END_MARKER = "// END GENERATED CELL_EM"
BEGIN_MARKER = "// BEGIN GENERATED one-cell"
END_MARKER = "// END GENERATED one-cell"
RUNS_PER_LINE = 6


def runs(codepoints) -> list[tuple[int, int]]:
    """Collapse code points into sorted inclusive (first, last) runs."""
    out: list[tuple[int, int]] = []
    for cp in sorted(set(codepoints)):
        if out and cp == out[-1][1] + 1:
            out[-1] = (out[-1][0], cp)
        else:
            out.append((cp, cp))
    return out


def render_block(codepoints) -> str:
    """Return the generated block, markers included, ending with a newline."""
    entries = [f"[0x{lo:04x}, 0x{hi:04x}]," for lo, hi in runs(codepoints)]
    lines = [BEGIN_MARKER, f"// Source: {MANIFEST_PATH.relative_to(REPO_ROOT).as_posix()} ({MANIFEST_KEY})."]
    lines.append("export const ONE_CELL_RUNS = Object.freeze([")
    for i in range(0, len(entries), RUNS_PER_LINE):
        lines.append("  " + " ".join(entries[i : i + RUNS_PER_LINE]))
    lines.append("]);")
    lines.append(END_MARKER)
    return "\n".join(lines) + "\n"


def render_cell_em(cell: dict) -> str:
    """Return the generated CELL_EM line, markers included, ending with a newline."""
    advance, upem = int(cell["advance"]), int(cell["upem"])
    lines = [
        CELL_MARKER,
        f"// Source: {MANIFEST_PATH.relative_to(REPO_ROOT).as_posix()} (cell_advance).",
        f"export const CELL_EM = {advance} / {upem};",
        CELL_END_MARKER,
    ]
    return "\n".join(lines) + "\n"


def load_cell_advance(path: Path = MANIFEST_PATH) -> dict:
    return load_manifest(path)["cell_advance"]


def load_codepoints(path: Path = MANIFEST_PATH) -> list[int]:
    return load_manifest(path)[MANIFEST_KEY]


def load_manifest(path: Path = MANIFEST_PATH) -> dict:
    """Return the bundled face's committed code point manifest."""
    return json.loads(path.read_text(encoding="utf-8"))


def splice_marker(source: str, start_marker: str, end_marker: str, block: str) -> str:
    """Replace one generated block delimited by the given markers."""
    start = source.index(start_marker)
    end = source.index(end_marker, start) + len(end_marker)
    if source[end : end + 1] == "\n":
        end += 1
    return source[:start] + block + source[end:]


def splice(source: str, block: str) -> str:
    """Replace the generated block of ``source`` with ``block``."""
    source = splice_marker(source, CELL_MARKER, CELL_END_MARKER, render_cell_em(load_cell_advance()))
    return splice_marker(source, BEGIN_MARKER, END_MARKER, block)


def main() -> int:
    source = OUTPUT_PATH.read_text(encoding="utf-8")
    updated = splice(source, render_block(load_codepoints()))
    if updated != source:
        OUTPUT_PATH.write_text(updated, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
