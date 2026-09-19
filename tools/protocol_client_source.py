"""Canonical loader for the client-side Elosern protocol validator source.

The webclient protocol reducer was split (SRP) from the single
``web/static/webclient/js/elosern/protocol.js`` facade into the domain modules
under ``web/static/webclient/js/elosern/protocol/``. Parity contracts that
enforce Python/JS constant agreement scan *source text*, so they must now scan
the whole client validator corpus: the facade plus every module it wires.

This helper defines that corpus exactly once. Ordering is deterministic
(facade first, then sorted module files) so regex scans are stable.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

PROTOCOL_JS = REPO_ROOT / "web/static/webclient/js/elosern/protocol.js"
PROTOCOL_DIR = REPO_ROOT / "web/static/webclient/js/elosern/protocol"


def protocol_client_source() -> str:
    """Concatenated source of the shipped JS protocol validator modules."""
    parts = [PROTOCOL_JS.read_text(encoding="utf-8")]
    for path in sorted(PROTOCOL_DIR.rglob("*.js")):
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)
