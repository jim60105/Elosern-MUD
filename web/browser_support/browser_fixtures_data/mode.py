"""Boot-mode flag for the managed browser harness.

Slice of the former ``web/browser_support/browser_fixtures_data``
module; ships verbatim."""

from __future__ import annotations

import os


def synth_mode_enabled() -> bool:
    """Whether the harness boots with the synthetic catalogs (harness default)."""
    return os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS", "1") == "1"
