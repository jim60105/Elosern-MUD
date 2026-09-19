"""Canonical loader for the client-side Elosern protocol validator source.

The webclient protocol reducer was split (SRP) from the single
``web/static/webclient/js/elosern/protocol.js`` facade into the domain modules
under ``web/static/webclient/js/elosern/protocol/``. Parity contracts that
enforce Python/JS constant agreement scan *source text*, so they must now scan
the whole client validator corpus.

The corpus is defined by the module graph the shipped facade actually loads
(via Node's ``require`` cache), never by a directory glob: a stray or hostile
``.js`` file dropped into the package is not part of the shipped surface and
must not be scanned as if it were, while a missing module fails loudly at
require time instead of silently shrinking the corpus.

The corpus is cached per process; the module files are read as UTF-8.
"""

from __future__ import annotations

import functools
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

PROTOCOL_JS = REPO_ROOT / "web/static/webclient/js/elosern/protocol.js"

# Node prints every protocol-package file it actually loaded, facade included.
_LOAD_GRAPH_JS = r"""
const path = require("node:path");
const facade = process.argv[1];
require(facade);
const dir = path.join(path.dirname(facade), "protocol");
const loaded = Object.keys(require.cache)
  .filter((p) => p === facade || p.startsWith(dir + path.sep))
  .sort();
process.stdout.write(JSON.stringify(loaded));
"""


@functools.lru_cache(maxsize=1)
def protocol_client_modules() -> tuple[str, ...]:
    """Absolute paths of the loaded protocol modules (facade first, sorted)."""
    try:
        result = subprocess.run(
            ["node", "-e", _LOAD_GRAPH_JS, str(PROTOCOL_JS)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        # check=True's message omits node's stderr; the real reason (syntax
        # error, missing module) would otherwise be lost at first failure.
        stderr = (exc.stderr or "").strip().splitlines()[-8:]
        raise RuntimeError(
            "protocol module graph failed to load under node:\n"
            + "\n".join(stderr)
        ) from exc
    modules = json.loads(result.stdout)
    if not modules or modules[0] != str(PROTOCOL_JS):
        raise RuntimeError("protocol facade did not load as the corpus root")
    # Guard against a refactor that quietly stops requiring a domain module:
    # the corpus must shrink loudly here, not as a downstream regex miss.
    if len(modules) < 19:
        raise RuntimeError(
            f"protocol corpus shrank to {len(modules)} modules "
            "(expected at least 19 shipped files)"
        )
    return tuple(modules)


def protocol_client_source() -> str:
    """Concatenated source of the shipped JS protocol validator module graph."""
    parts = [Path(p).read_text(encoding="utf-8") for p in protocol_client_modules()]
    return "\n".join(parts)
