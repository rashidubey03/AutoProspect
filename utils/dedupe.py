from collections.abc import Callable, Iterable
from typing import TypeVar


T = TypeVar("T")
K = TypeVar("K")


def unique_by(items: Iterable[T], key: Callable[[T], K]) -> list[T]:
    seen: set[K] = set()
    unique_items: list[T] = []
    for item in items:
        item_key = key(item)
        if item_key in seen:
            continue
        seen.add(item_key)
        unique_items.append(item)
    return unique_items
