"""Import the self-hosted Jim Mono TC monospace slices and their stylesheet.

The WebClient's monospace token ``--f-mono`` draws Latin, box drawing, and CJK
with Jim Mono TC (https://github.com/jim60105/JimMonoTC, SIL OFL 1.1), a merge
of Hack 3.003 and Noto Sans CJK TC in which every CJK character is exactly two
Latin cells wide. The font's own release already cuts its web build into small
unicode-range woff2 slices, so this tool only imports them (openspec change
``webclient-jim-mono-tc-font``, design D0/D1):

1. download the pinned ``-web.zip`` release asset and verify its SHA-256;
2. keep the Regular (400) and Bold (700) slices of the one-cell groups
   (``latin``, ``latin-ext``, ``greek-cyrillic``, ``box``, ``symbols``) and the
   frequency CJK groups (``cjk-<N>``); drop the Nerd Fonts ``icons-<N>`` and the
   rare-CJK ``cjk-x<N>`` slices and the italic styles;
3. filter the release ``JimMonoTC.css`` to the kept rules and rewrite their
   URLs to project-relative paths;
4. refuse to write anything when a kept slice exceeds 64 KB or is not woff2,
   a kept file and its rule do not pair up, one weight's ranges overlap, the
   two weights declare different CJK, an ASCII code point sits outside
   ``latin``, or ``licenses/LICENSE`` is missing;
5. clear ``fonts/jimmonotc/`` and write the kept slices, the ``licenses/``
   tree, the ``codepoints.json`` manifest, and ``styles/fonts-mono.css``.

Run: ``uv run --locked python -m tools.import_mono_font`` (network needed), or
pass a local copy of the release asset as the only argument; its SHA-256 is
verified either way. Standard library only, and a second run is
byte-identical.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import stat
import shutil
import sys
import unicodedata
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "web/webclient-app"
FONT_DIR = APP_ROOT / "fonts/jimmonotc"
CSS_PATH = APP_ROOT / "styles/fonts-mono.css"
MANIFEST_PATH = FONT_DIR / "codepoints.json"
NOTO_CSS_PATH = APP_ROOT / "styles/fonts.css"

RELEASE = "v0.2.0"
ASSET = "JimMonoTC-0.2.0-web.zip"
ASSET_URL = f"https://github.com/jim60105/JimMonoTC/releases/download/{RELEASE}/{ASSET}"
# From the release's SHA256SUMS.txt.
ASSET_SHA256 = "ac2c338253c4d5263de747198b1ffdd7a155552fb39aaa4537e5c01a5de08dab"

FAMILY = "Jim Mono TC"
# Release style name -> (manifest key, CSS font-weight).
STYLES = {"Regular": ("regular", 400), "Bold": ("bold", 700)}
ONE_CELL_GROUPS = ("latin", "latin-ext", "greek-cyrillic", "box", "symbols")
CJK_GROUP = re.compile(r"cjk-\d+")
FILE_NAME = re.compile(r"JimMonoTC-(?P<style>[A-Za-z]+)\.(?P<group>[a-z0-9-]+)\.woff2")
MAX_SLICE_BYTES = 65536
ASCII = set(range(0x20, 0x7F))
# The latin slice owns the arrows the dock legend and help table draw.
ARROWS = set(range(0x2190, 0x2194))
LICENSE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*(/[A-Za-z0-9][A-Za-z0-9._-]*)*")


class ReleaseContractError(ValueError):
    """The release breaks the import contract; nothing is written."""


def parse_ranges(value: str) -> set[int]:
    """Expand a CSS unicode-range value into its code points."""
    out: set[int] = set()
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        lo, _, hi = part.upper().removeprefix("U+").partition("-")
        out.update(range(int(lo, 16), int(hi or lo, 16) + 1))
    return out


def parse_css(text: str) -> list[dict]:
    """Parse ``@font-face`` rules into ordered property lists plus metadata.

    Each rule is ``{"props": [(name, value), ...], "file": <basename>,
    "style": <release style>, "group": <group>, "codepoints": set}``.
    """
    rules = []
    for body in re.findall(r"@font-face\s*\{(.*?)\}", text, re.S):
        props = []
        for decl in body.split(";"):
            name, sep, value = decl.partition(":")
            if sep:
                props.append((name.strip(), value.strip()))
        values = dict(props)
        src = re.fullmatch(r"""url\(["']?([^"')]+)["']?\)\s*format\(["']?woff2["']?\)""", values.get("src", ""))
        if src is None:
            raise ReleaseContractError(f"unsupported src in rule: {values.get('src')!r}")
        file = src.group(1).rsplit("/", 1)[-1]
        match = FILE_NAME.fullmatch(file)
        if match is None:
            raise ReleaseContractError(f"unexpected slice file name {file!r}")
        rules.append({
            "props": props,
            "file": file,
            "style": match["style"],
            "group": match["group"],
            "codepoints": parse_ranges(values.get("unicode-range", "")),
        })
    return rules


def is_kept(style: str, group: str) -> bool:
    return style in STYLES and (group in ONE_CELL_GROUPS or CJK_GROUP.fullmatch(group) is not None)


def render_css(rules: list[dict]) -> str:
    """Re-emit the kept rules in release order with project-relative URLs."""
    lines = [
        "/*",
        " * GENERATED by tools/import_mono_font.py -- do not edit by hand.",
        f" * Jim Mono TC {RELEASE} (https://github.com/jim60105/JimMonoTC), SIL Open Font",
        " * License 1.1 (../fonts/jimmonotc/licenses/LICENSE). Self-hosted unicode-range",
        " * woff2 slices for the --f-mono type role, served from the project origin.",
        " */",
    ]
    for rule in rules:
        lines += ["", "@font-face {"]
        for name, value in rule["props"]:
            if name == "src":
                value = f"url(../fonts/jimmonotc/{rule['file']}) format('woff2')"
            lines.append(f"  {name}: {value};")
        lines.append("}")
    return "\n".join(lines) + "\n"


def noto_coverage(text: str) -> set[int]:
    """Code points of the bundled Noto Sans TC weight-400 faces in fonts.css."""
    out: set[int] = set()
    for body in re.findall(r"@font-face\s*\{(.*?)\}", text, re.S):
        if re.search(r"font-family:\s*['\"]Noto Sans TC['\"]", body) and re.search(r"font-weight:\s*400;", body):
            out |= parse_ranges(re.search(r"unicode-range:\s*([^;]+);", body).group(1))
    return out


def is_wide(cp: int) -> bool:
    return unicodedata.east_asian_width(chr(cp)) in ("W", "F")


def build_manifest(rules: list[dict], noto: set[int]) -> dict:
    """Derive the per-weight one-cell and CJK sets from the kept rules."""
    manifest: dict = {"release": RELEASE}
    cjk: dict[str, list[int]] = {}
    for style, (key, _weight) in STYLES.items():
        mine = [rule for rule in rules if rule["style"] == style]
        one = set().union(*(r["codepoints"] for r in mine if r["group"] in ONE_CELL_GROUPS))
        manifest[key] = sorted(one)
        cjk[key] = sorted(set().union(*(r["codepoints"] for r in mine if CJK_GROUP.fullmatch(r["group"]))))
    manifest["cjk"] = cjk
    declared = set(cjk["regular"])
    manifest["noto_wide_missing"] = sorted(cp for cp in noto if is_wide(cp) and cp not in declared)
    return manifest


def check(rules: list[dict], files: dict[str, bytes], has_license: bool) -> None:
    """Raise ReleaseContractError when the kept rules and files break the contract."""
    problems = []
    for name, data in sorted(files.items()):
        if len(data) > MAX_SLICE_BYTES:
            problems.append(f"{name} is {len(data)} bytes (> {MAX_SLICE_BYTES})")
        if data[:4] != b"wOF2":
            problems.append(f"{name} is not woff2")
    ruled = [rule["file"] for rule in rules]
    if len(set(ruled)) != len(ruled):
        problems.append("a slice file is declared by more than one rule")
    for name in sorted(set(files) - set(ruled)):
        problems.append(f"{name} has no CSS rule")
    for name in sorted(set(ruled) - set(files)):
        problems.append(f"CSS rule for {name} has no file")
    for style, (key, weight) in STYLES.items():
        mine = [rule for rule in rules if rule["style"] == style]
        groups = {rule["group"] for rule in mine}
        missing = set(ONE_CELL_GROUPS) - groups
        if missing:
            problems.append(f"{style} lacks groups {sorted(missing)}")
        seen: set[int] = set()
        for rule in mine:
            values = dict(rule["props"])
            if values.get("font-weight") != str(weight) or values.get("font-style") != "normal":
                problems.append(f"{rule['file']} declares weight/style {values.get('font-weight')}/{values.get('font-style')}")
            if values.get("font-family", "").strip("\"'") != FAMILY:
                problems.append(f"{rule['file']} declares family {values.get('font-family')}")
            if not rule["codepoints"]:
                problems.append(f"{rule['file']} declares no unicode-range")
            if seen & rule["codepoints"]:
                problems.append(f"{rule['file']} overlaps an earlier {style} rule")
            seen |= rule["codepoints"]
            if rule["group"] != "latin" and rule["codepoints"] & (ASCII | ARROWS):
                problems.append(f"{rule['file']} declares ASCII or an arrow outside latin")
    cjk = {
        style: set().union(*(r["codepoints"] for r in rules if r["style"] == style and CJK_GROUP.fullmatch(r["group"])))
        for style in STYLES
    }
    if cjk["Regular"] != cjk["Bold"]:
        problems.append("Regular and Bold declare different CJK code points")
    if not has_license:
        problems.append("licenses/LICENSE is missing")
    if problems:
        raise ReleaseContractError("; ".join(problems))


def read_release(archive: bytes) -> tuple[str, dict[str, bytes], dict[str, bytes]]:
    """Return (release CSS, kept woff2 files by name, licence files by relative path)."""
    css = None
    files: dict[str, bytes] = {}
    licenses: dict[str, bytes] = {}
    seen: set[str] = set()
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            _root, _, rel = info.filename.partition("/")
            if rel in seen:
                raise ReleaseContractError(f"duplicate member {info.filename}")
            seen.add(rel)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ReleaseContractError(f"{info.filename} is a symbolic link")
            if rel == "JimMonoTC.css":
                css = zf.read(info).decode("utf-8")
            elif rel.startswith("licenses/"):
                name = rel.removeprefix("licenses/")
                # Keep every licence member inside fonts/jimmonotc/licenses/.
                if not LICENSE_NAME.fullmatch(name) or ".." in PurePosixPath(name).parts:
                    raise ReleaseContractError(f"unsafe licence member name {info.filename!r}")
                licenses[name] = zf.read(info)
            elif "/" not in rel and (match := FILE_NAME.fullmatch(rel)) and is_kept(match["style"], match["group"]):
                files[rel] = zf.read(info)
    if css is None:
        raise ReleaseContractError("JimMonoTC.css is missing from the release")
    return css, files, licenses


def build(archive: bytes, noto_css: str) -> dict[str, bytes]:
    """Return every output file (path relative to APP_ROOT -> bytes)."""
    css, files, licenses = read_release(archive)
    rules = [rule for rule in parse_css(css) if is_kept(rule["style"], rule["group"])]
    check(rules, files, "LICENSE" in licenses)
    manifest = build_manifest(rules, noto_coverage(noto_css))
    out = {f"fonts/jimmonotc/{name}": data for name, data in files.items()}
    out.update({f"fonts/jimmonotc/licenses/{rel}": data for rel, data in licenses.items()})
    out["fonts/jimmonotc/codepoints.json"] = (json.dumps(manifest, separators=(",", ":")) + "\n").encode()
    out["styles/fonts-mono.css"] = render_css(rules).encode()
    return out


def fetch(source: str | None) -> bytes:
    if source is None:
        with urllib.request.urlopen(ASSET_URL, timeout=120) as response:
            data = response.read()
    else:
        data = Path(source).read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != ASSET_SHA256:
        raise SystemExit(f"checksum mismatch for {source or ASSET_URL}: {digest}")
    return data


def write(outputs: dict[str, bytes]) -> None:
    """Stage the font tree and the sheet beside their targets, then swap them in.

    The old tree is renamed aside (not deleted) before the new one takes its
    place and only removed afterwards, and the sheet is replaced atomically
    last, so an interrupted run leaves either the old or the new outputs in
    place plus, at worst, an untracked ``.tmp`` / ``.old`` sibling.
    """
    staging = FONT_DIR.with_name(FONT_DIR.name + ".tmp")
    retired = FONT_DIR.with_name(FONT_DIR.name + ".old")
    css_staging = CSS_PATH.with_name(CSS_PATH.name + ".tmp")
    prefix = "fonts/jimmonotc/"
    shutil.rmtree(staging, ignore_errors=True)
    shutil.rmtree(retired, ignore_errors=True)
    try:
        for rel, data in sorted(outputs.items()):
            if rel.startswith(prefix):
                path = staging / rel.removeprefix(prefix)
                if not path.resolve().is_relative_to(staging.resolve()):
                    raise SystemExit(f"refusing to write outside {FONT_DIR}: {rel}")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        css_staging.write_bytes(outputs["styles/fonts-mono.css"])
        if FONT_DIR.exists():
            os.replace(FONT_DIR, retired)
        os.replace(staging, FONT_DIR)
        os.replace(css_staging, CSS_PATH)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        css_staging.unlink(missing_ok=True)
    shutil.rmtree(retired, ignore_errors=True)


def main(argv: list[str]) -> int:
    archive = fetch(argv[0] if argv else None)
    try:
        outputs = build(archive, NOTO_CSS_PATH.read_text(encoding="utf-8"))
    except ReleaseContractError as exc:
        print(f"refusing to import: {exc}", file=sys.stderr)
        return 1
    write(outputs)
    slices = [rel for rel in outputs if rel.endswith(".woff2")]
    print(f"wrote {len(slices)} slices ({sum(len(outputs[r]) for r in slices)} bytes) from {ASSET}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
