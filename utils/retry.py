from collections.abc import Callable
from time import sleep
from typing import TypeVar


T = TypeVar("T")


class RetryError(RuntimeError):
    pass


def retry(
    action: Callable[[], T],
    *,
    attempts: int = 3,
    initial_delay_seconds: float = 1.0,
    backoff_factor: float = 2.0,
) -> T:
    last_error: Exception | None = None
    delay = initial_delay_seconds

    for attempt_number in range(1, attempts + 1):
        try:
            return action()
        except Exception as error:
            last_error = error
            if attempt_number == attempts:
                break
            sleep(delay)
            delay *= backoff_factor

    raise RetryError(f"Action failed after {attempts} attempts") from last_error
