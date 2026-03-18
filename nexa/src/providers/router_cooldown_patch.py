
import time

DEFAULT_COOLDOWN_SECONDS = 5


def update_provider_health_on_failure(provider, error):
    retryable = getattr(error, "retryable", False)
    if not retryable:
        return

    health = getattr(provider, "health", None)
    if health is None:
        return

    health.healthy = False
    health.last_error = type(error).__name__
    health.cooldown_until = time.time() + DEFAULT_COOLDOWN_SECONDS
