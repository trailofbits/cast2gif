from collections.abc import MutableSet
from typing import Dict, Generic, Hashable, Iterable, Iterator, TypeVar

T = TypeVar("T", bound=Hashable)


class OrderedMutableSet(Generic[T], MutableSet[T]):
    def __init__(self, items: Iterable[T] = ()):
        super().__init__()
        self._keys: Dict[T: None] = dict.fromkeys(items)

    def add(self, value: T) -> None:
        if value not in self._keys:
            self._keys[value] = None

    def discard(self, value: T) -> None:
        del self._keys[value]

    def __contains__(self, x: object) -> bool:
        return x in self._keys

    def __len__(self) -> int:
        return len(self._keys)

    def __iter__(self) -> Iterator[T]:
        return iter(self._keys.keys())


if __name__ == "__main__":
    keywords = ['foo', 'bar', 'bar', 'foo', 'baz', 'foo']
    oms: OrderedMutableSet[str] = OrderedMutableSet()
    for keyword in keywords:
        oms.add(keyword)
    assert list(oms) == ['foo', 'bar', 'baz']
