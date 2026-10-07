"""Composition root for an intentional optional reply attempt."""

from world.observability import log_warn


def _letter_body(source_id):
    """The incoming letter body for the failure event, or None if unreadable."""
    from world.narrative.correspondence import get_letter

    try:
        return get_letter(source_id).body
    except Exception:  # observability: ignore R2: the enclosing correspondence_reply_failed event reports the failure; the body is optional context
        return None


def request_letter_reply(source_id, *, client=None):
    """Attempt once; no startup sweep, retry loop, or guaranteed response."""
    from world.ai.client import OpenAICompatClient
    from world.ai.guardrail import CallIdTap
    from world.ai.profiles import get_profile
    from world.narrative.replies import attempt_reply

    injected = client if client is not None else OpenAICompatClient(get_profile("correspondence"))
    # A fresh tap per attempt names the actual guarded call in the failure
    # event; it stays None when the failure precedes any guarded call.
    tap = CallIdTap(injected)
    result = attempt_reply(source_id, tap)

    def failed(failure):
        log_warn("correspondence_reply_failed", context={
            "source_id": source_id, "body": _letter_body(source_id),
            "call_id": tap.latest,
        }, exc=failure.value)
        return None

    result.addErrback(failed)
    return result
