"""Isolated scratch settings for the manual monster-AI report tool.

Imported as ``DJANGO_SETTINGS_MODULE`` by ``tools/monster_ai_manual_reports.py``
*after* ``MUD_MANUAL_REPORT_DB`` names a fresh scratch file, so the default
connection is the scratch database from the moment Django initializes: the
developer's live database (``server/db/evennia.db3``) and the retained Evennia
test database are never opened, not even by an import-time table read.

Manual acceptance tooling only: nothing in the game runtime or the default test
suite imports this module.
"""

from __future__ import annotations

import os

from server.conf.settings import *  # noqa: F401,F403

#: The scratch database the tool created for this run. Assigned before Django
#: opens any connection, so the override can never race an initialization read.
DATABASES["default"]["NAME"] = os.environ["MUD_MANUAL_REPORT_DB"]

# Manual evidence never reaches a model or network service: the transcript sink
# stays off so no manual run writes into the real server transcript either.
LLM_TRANSCRIPT_ENABLED = False