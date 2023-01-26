import json
from typing import Any, Dict, Iterable, Type, Union

from .recording import AutoTerminalSize, C, InheritedTerminalSize, TerminalOutput, TerminalRecording, TerminalSize


class AsciiCast(TerminalRecording):
    def __init__(self, terminal_size: TerminalSize = AutoTerminalSize()):
        super().__init__(terminal_size)

        self._metadata: Dict[str, Any] = {}

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata

    @metadata.setter
    def metadata(self, new_metadata: Dict[str, Any]):
        if "width" in new_metadata and isinstance(self._size, InheritedTerminalSize) and self._size.width_was_inherited:
            self._size.width = new_metadata["width"]
            self._size.width_was_inherited = False
        if "height" in new_metadata and isinstance(self._size, InheritedTerminalSize) \
                and self._size.height_was_inherited:
            self._size.height = new_metadata["height"]
            self._size.height_was_inherited = False
        self._metadata = new_metadata

    @classmethod
    def load(cls: Type[C], cast: Union[bytes, str, Iterable[str]],
             terminal_size: TerminalSize = InheritedTerminalSize()) -> C:
        if isinstance(cast, str) or isinstance(cast, bytes):
            cast = cast.splitlines()

        ascii_cast = cls(terminal_size=terminal_size)

        for i, line in enumerate(cast):
            if i == 0:
                ascii_cast.metadata = json.loads(line)
            else:
                event_time, event_type, data = json.loads(line)
                if event_type == "o":
                    ascii_cast.events.append(TerminalOutput(data, time=event_time))

        return ascii_cast
