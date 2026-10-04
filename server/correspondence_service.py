"""Composition root for an intentional optional reply attempt."""

from world.observability import log_warn


def request_letter_reply(source_id, *, client=None):
    """Attempt once; no startup sweep, retry loop, or guaranteed response."""
    from world.ai.client import OpenAICompatClient
    from world.ai.profiles import get_profile
    from world.narrative.replies import attempt_reply

    injected = client if client is not None else OpenAICompatClient(get_profile("correspondence"))
    result = attempt_reply(source_id, injected)

    def failed(failure):
        log_warn("correspondence_reply_failed", context={"source_id": source_id},
                 exc=failure.value)
        return None

    result.addErrback(failed)
    return result
