
import time


def provider_available(provider):
    health = getattr(provider, "health", None)
    if health is None:
        return True

    if health.cooldown_until is None:
        return True

    return health.cooldown_until <= time.time()
