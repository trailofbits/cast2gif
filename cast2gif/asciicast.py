import json
from typing import Any, Dict, Iterable, Optional, Type, Union

from .recording import C, TerminalOutput, TerminalRecording


class AsciiCast(TerminalRecording):
    def __init__(self, width: Optional[int] = None, height: Optional[int] = None):
        super().__init__(width=width, height=height)

        self._metadata: Dict[str, Any] = {}

    @property
    def metadata(self) -> Dict[str, Any]:
        return self._metadata

    @metadata.setter
    def metadata(self, new_metadata: Dict[str, Any]):
        if "width" in new_metadata:
            self.width = new_metadata["width"]
        if "height" in new_metadata:
            self.height = new_metadata["height"]
        self._metadata = new_metadata

    @classmethod
    def load(cls: Type[C], cast: Union[bytes, str, Iterable[str]],
             width: Optional[int] = None, height: Optional[int] = None) -> C:
        if isinstance(cast, str) or isinstance(cast, bytes):
            cast = cast.splitlines()

        ascii_cast = cls(width=width, height=height)

        for i, line in enumerate(cast):
            if i == 0:
                ascii_cast.metadata = json.loads(line)
                if width is not None:
                    # override the original metadata
                    ascii_cast.width = width
                if height is not None:
                    # override the original metadata
                    ascii_cast.height = height
            else:
                event_time, event_type, data = json.loads(line)
                if event_type == "o":
                    ascii_cast.events.append(TerminalOutput(data, time=event_time))

        return ascii_cast
