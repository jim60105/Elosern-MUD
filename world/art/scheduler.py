"""The settings-configurable, disableable periodic art drain Script.

``ArtDrainScript`` is a persistent ``DefaultScript`` that drains up to
``ART_SCHEDULER_LIMIT`` pending jobs every ``ART_SCHEDULER_INTERVAL_SECONDS``.
When ``ART_SCHEDULER_ENABLED`` is false the Script exists but never drains;
records remain ``missing``/``pending``, placeholders remain, and gameplay
proceeds unchanged (design D8). Art is wall-clock time, independent of the
player-driven world clock.
"""

from django.conf import settings

from evennia import DefaultScript


class ArtDrainScript(DefaultScript):
    """Periodically drains the shared art queue through the worker boundary."""

    def at_script_creation(self) -> None:
        self.interval = settings.ART_SCHEDULER_INTERVAL_SECONDS
        self.start_delay = True
        self.repeats = 0

    def at_repeat(self) -> None:
        if not settings.ART_SCHEDULER_ENABLED:
            return
        from world.art.worker import drain

        drain(settings.ART_SCHEDULER_LIMIT)
