# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "fonttools==4.66.1",
#     "brotli==1.2.0",
# ]
# ///
"""Generate the self-hosted Hack monospace slices and their stylesheet.

The WebClient's monospace token ``--f-mono`` draws Latin, digits, arrows, and
box drawing with Hack (https://github.com/source-foundry/Hack, MIT + Bitstream
Vera license). Like the Iansui / Noto faces, Hack is served from the project
origin as small unicode-range woff2 slices, so a page downloads only the
slices whose characters it draws. This script is the one reproducible way to
produce them (openspec change ``webclient-hack-mono-font``, design D1-D6):

1. download the upstream v3.003 TTF release and the tag's ``LICENSE.md`` and
   verify both pinned SHA-256 digests;
2. assign each Hack code point to the first slice whose claim window holds it;
3. subset each (weight, slice) with fontTools, keeping the TrueType hinting,
   into woff2 with the upstream ``head.modified`` timestamp kept, twice, and
   fail if the two byte streams differ;
4. write the slices, the license, a per-weight code-point manifest, and the
   generated ``styles/fonts-hack.css``;
5. print a size table and fail if a slice leaves the 4-40 KB band.

Run it with ``uv run --script tools/gen_hack_font_slices.py``. The pinned
fontTools / brotli live in the inline metadata above, not in the project lock:
the game runtime never imports them, and the helpers below import nothing
outside the standard library so ``tests/test_hack_font_slices_tool.py`` runs in
the project environment.
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "web/webclient-app"
FONT_DIR = APP_ROOT / "fonts/hack"
CSS_PATH = APP_ROOT / "styles/fonts-hack.css"
MANIFEST_PATH = FONT_DIR / "codepoints.json"

VERSION = "v3.003"
ARCHIVE_URL = f"https://github.com/source-foundry/Hack/releases/download/{VERSION}/Hack-{VERSION}-ttf.tar.xz"
ARCHIVE_SHA256 = "d9ed5d0a07525c7e7bd587b4364e4bc41021dd668658d09864453d9bb374a78d"
LICENSE_URL = f"https://raw.githubusercontent.com/source-foundry/Hack/{VERSION}/LICENSE.md"
LICENSE_SHA256 = "1f61bb7c790c59b4b0ecdf304628b94e42ae4c8020094a8c3da73381ab212623"

# (weight name, CSS font-weight, TTF member name inside the release archive).
WEIGHTS = (
    ("regular", 400, "./Hack-Regular.ttf"),
    ("bold", 700, "./Hack-Bold.ttf"),
)

# Slices in claim order. A code point belongs to the FIRST slice whose claim
# window holds it, so the windows may overlap (arrows sit in both `latin` and
# `symbols`; `latin` takes typographic punctuation out of `latin-ext`), while
# the declared unicode-ranges are built from the disjoint claimed sets.
SLICES = (
    ("latin", (
        (0x0020, 0x007E), (0x00A0, 0x00FF), (0x2013, 0x2014), (0x2018, 0x201F),
        (0x2022, 0x2022), (0x2026, 0x2026), (0x2039, 0x203A), (0x20AC, 0x20AC),
        (0x2122, 0x2122), (0x2190, 0x2193), (0xFFFD, 0xFFFD),
    )),
    ("latin-ext", (
        (0x0100, 0x036F), (0x0E3F, 0x0E3F), (0x1E00, 0x1EFF), (0x2000, 0x218F),
        (0x2C60, 0x2C7F),
    )),
    ("greek-cyrillic", ((0x0370, 0x03FF), (0x0400, 0x058F), (0x10A0, 0x10FF), (0x1F00, 0x1FFF))),
    ("box", ((0x2500, 0x259F),)),
    ("symbols", ((0x2190, 0x23FF), (0x25A0, 0x2BFF), (0x2E00, 0x2E7F), (0xE000, 0xF8FF))),
)

# cmap entries that need no glyph slice: NUL, CR, and the byte-order mark
# (a default-ignorable format character).
EXCLUDED = frozenset({0x0000, 0x000D, 0xFEFF})

# Vite inlines assets under its 4096-byte assetsInlineLimit as data URIs; the
# upper bound is the spec's small-file ceiling.
MIN_SLICE_BYTES = 4096
MAX_SLICE_BYTES = 40960


def assign(codepoints) -> dict[str, list[int]]:
    """Map each slice name to the sorted code points it claims first.

    Code points outside every claim window are dropped.
    """
    claimed: set[int] = set()
    result: dict[str, list[int]] = {}
    for name, windows in SLICES:
        mine = sorted(
            cp for cp in set(codepoints) - claimed
            if any(lo <= cp <= hi for lo, hi in windows)
        )
        claimed.update(mine)
        result[name] = mine
    return result


def runs(codepoints) -> list[tuple[int, int]]:
    """Collapse code points into sorted inclusive (first, last) runs."""
    out: list[tuple[int, int]] = []
    for cp in sorted(set(codepoints)):
        if out and cp == out[-1][1] + 1:
            out[-1] = (out[-1][0], cp)
        else:
            out.append((cp, cp))
    return out


def unicode_range(codepoints) -> str:
    """Render a CSS unicode-range value in the lowercase style of fonts.css."""
    return ", ".join(
        f"U+{lo:x}" if lo == hi else f"U+{lo:x}-{hi:x}" for lo, hi in runs(codepoints)
    )


def slice_filename(weight: str, name: str) -> str:
    return f"hack-{weight}.{name}.woff2"


def render_css(claimed_by_weight: dict[str, dict[str, list[int]]]) -> str:
    """Render the generated @font-face stylesheet for every (weight, slice).

    Raises ValueError when two slices of one weight would declare overlapping
    ranges: browsers resolve overlaps last-declared-wins, not first-claim.
    """
    lines = [
        "/*",
        " * GENERATED by tools/gen_hack_font_slices.py -- do not edit by hand.",
        f" * Hack {VERSION} (https://github.com/source-foundry/Hack), MIT + Bitstream",
        " * Vera license (../fonts/hack/LICENSE.md). Self-hosted unicode-range woff2",
        " * slices for the --f-mono type role, served from the project origin.",
        " */",
    ]
    for weight, css_weight, _member in WEIGHTS:
        seen: set[int] = set()
        for name, _windows in SLICES:
            cps = claimed_by_weight[weight][name]
            if seen & set(cps):
                raise ValueError(f"{weight}.{name} overlaps an earlier slice")
            seen.update(cps)
            lines += [
                "",
                "@font-face {",
                "  font-family: 'Hack';",
                "  font-style: normal;",
                f"  font-weight: {css_weight};",
                "  font-display: swap;",
                f"  src: url(../fonts/hack/{slice_filename(weight, name)}) format('woff2');",
                f"  unicode-range: {unicode_range(cps)};",
                "}",
            ]
    return "\n".join(lines) + "\n"


def _fetch(url: str, sha256: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != sha256:
        raise SystemExit(f"checksum mismatch for {url}: {digest}")
    return data


def _subset(ttf: bytes, codepoints: list[int]) -> bytes:
    from fontTools import subset
    from fontTools.ttLib import TTFont

    # recalcTimestamp=False keeps the upstream head.modified, so every run
    # produces the same bytes.
    font = TTFont(io.BytesIO(ttf), recalcTimestamp=False)
    options = subset.Options()
    options.layout_features = ["*"]
    options.name_IDs = [0, 1, 2, 3, 4, 5, 6, 13, 14]
    options.name_languages = [0x409]
    options.glyph_names = False
    options.notdef_outline = True
    options.hinting = True
    options.drop_tables = [*options.drop_tables, "TTFA"]
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=codepoints)
    subsetter.subset(font)
    # The subsetter's flavor option alone does not switch the saved flavor.
    font.flavor = "woff2"
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


def main() -> int:
    from fontTools.ttLib import TTFont

    archive = _fetch(ARCHIVE_URL, ARCHIVE_SHA256)
    license_text = _fetch(LICENSE_URL, LICENSE_SHA256)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:xz") as tar:
        ttfs = {weight: tar.extractfile(member).read() for weight, _c, member in WEIGHTS}

    manifest: dict[str, list[int]] = {}
    claimed_by_weight: dict[str, dict[str, list[int]]] = {}
    slices: dict[str, bytes] = {}
    for weight, _css_weight, _member in WEIGHTS:
        cmap = set(TTFont(io.BytesIO(ttfs[weight])).getBestCmap()) - EXCLUDED
        claimed = assign(cmap)
        unclaimed = cmap - {cp for cps in claimed.values() for cp in cps}
        if unclaimed:
            raise SystemExit(f"{weight}: unclaimed code points {sorted(map(hex, unclaimed))}")
        manifest[weight] = sorted(cmap)
        claimed_by_weight[weight] = claimed
        for name, _windows in SLICES:
            if not claimed[name]:
                raise SystemExit(f"{weight}.{name} claims no code point")
            first = _subset(ttfs[weight], claimed[name])
            if _subset(ttfs[weight], claimed[name]) != first:
                raise SystemExit(f"{weight}.{name} is not byte-reproducible")
            slices[slice_filename(weight, name)] = first

    css = render_css(claimed_by_weight)
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, data in slices.items():
        (FONT_DIR / filename).write_bytes(data)
    (FONT_DIR / "LICENSE.md").write_bytes(license_text)
    MANIFEST_PATH.write_text(json.dumps(manifest, separators=(",", ":")) + "\n", encoding="utf-8")
    CSS_PATH.write_text(css, encoding="utf-8")

    failed = False
    for filename, data in slices.items():
        ok = MIN_SLICE_BYTES <= len(data) <= MAX_SLICE_BYTES
        failed |= not ok
        print(f"{filename:36} {len(data):7} bytes{'' if ok else '  OUT OF BAND'}")
    print(f"{'total':36} {sum(map(len, slices.values())):7} bytes")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
