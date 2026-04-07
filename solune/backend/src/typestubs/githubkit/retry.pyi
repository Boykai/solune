from typing import Any

class RetryChainDecision:
    """Decision from a retry chain."""
    def __init__(self, *decisions: Any) -> None: ...

RETRY_RATE_LIMIT: Any
RETRY_SERVER_ERROR: Any
