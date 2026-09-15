"""Action-evidence kind vocabulary (light-penance-events).

Single source for the evidence-kind strings the trusted recent-action
evidence store attests. ``world/rules/action_evidence.py`` re-exports this
value and owns every recording/querying rule; the vocabulary itself is
static world data, so it lives here beside the other closed vocabularies.
"""

EVIDENCE_KINDS: frozenset[str] = frozenset({"forced_interaction"})

__all__ = ["EVIDENCE_KINDS"]
