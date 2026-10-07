"""Stable owner refusals shared by console execution and transports."""


class ConsoleError(Exception):
    """A validated refusal, distinct from an unexpected execution failure."""

    def __init__(self, code: str, reason: str = ""):
        super().__init__(reason or code)
        self.code = code
        self.reason = reason
        self.snapshot = {"taken": False, "save_id": None}
