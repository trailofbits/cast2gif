import codecs
import math
import os
import pty
from select import select
import sys
import termios
import time as time_module
import tty
from typing import BinaryIO, Callable, Generic, Iterable, List, Optional, Type, TypeVar, Union

from PIL.ImageFont import FreeTypeFont

from .fonts import FontCollection
from .terminal import ANSITerminal, InfiniteWidthTerminal


C = TypeVar("C")


class TerminalEvent:
    def __init__(self, time: Optional[float] = None):
        if time is None:
            time = time_module.time()
        self.time: float = time


class TerminalOutput(TerminalEvent):
    def __init__(self, data: str, time: Optional[float] = None):
        super().__init__(time)
        self.data: str = data


from typing import Protocol, runtime_checkable


@runtime_checkable
class ConstantTerminalSize(Protocol):
    width: int
    height: int


@runtime_checkable
class DynamicTerminalSize(Protocol):
    @property
    def width(self) -> int:
        return 0

    @property
    def height(self) -> int:
        return 0


TerminalSize = Union[ConstantTerminalSize, DynamicTerminalSize]


class FixedTerminalSize(ConstantTerminalSize):
    def __init__(self, width: int = 80, height: int = 24):
        self.width: int = width
        self.height: int = height


class InheritedTerminalSize(FixedTerminalSize):
    def __init__(self, width: Optional[int] = None, height: Optional[int] = None):
        if width is None or height is None:
            try:
                term_size = os.get_terminal_size()
                if width is None and term_size.columns > 0:
                    width = term_size.columns
                if height is None and term_size.lines > 0:
                    height = term_size.lines
            except OSError:
                pass
        if width is None:
            width = 80
        if height is None:
            height = 24
        super().__init__(width=width, height=height)


class AutoTerminalSize(DynamicTerminalSize):
    def __init__(self):
        self.recording: Optional[TerminalRecording] = None
        self._width: int = -1
        self._height: int = -1

    @property
    def width(self) -> int:
        if self.recording is None:
            return InheritedTerminalSize().width
        elif self._width < 0:
            term = InfiniteWidthTerminal()
            for i, event in enumerate(self.recording.events):
                if not isinstance(event, TerminalOutput):
                    continue
                term.write(event.data)
            self._width = term.maximum_width
        return self._width

    @property
    def height(self) -> int:
        if self._height < 0:
            self._height = InheritedTerminalSize().height
        return self._height


class TerminalRecording:
    def __init__(self, terminal_size: TerminalSize = InheritedTerminalSize()):
        self._size: TerminalSize = None  # type: ignore
        self.size = terminal_size
        self.return_value: Optional[int] = None
        self.events: List[TerminalEvent] = []

    @property
    def size(self) -> TerminalSize:
        return self._size

    @size.setter
    def size(self, new_size: TerminalSize):
        if isinstance(self._size, AutoTerminalSize):
            self._size.recording = None
        if isinstance(new_size, AutoTerminalSize):
            if new_size.recording is not None and new_size.recording is not self:
                raise ValueError("The auto terminal size object is already assigned to a different recording")
            new_size.recording = self
        self._size = new_size

    @classmethod
    def record(cls: Type[C], argv: Iterable[str], terminal_size: TerminalSize = InheritedTerminalSize(),
               encoding: str = "utf-8", ps1: Optional[str] = None) -> C:
        recorder = TerminalRecorder(recording=cls(terminal_size), encoding=encoding)
        recording = recorder.record(argv)
        if ps1 is not None:
            new_events: List[TerminalEvent] = [
                TerminalOutput(f"{ps1}{' '.join(argv)}\n", 0.0)
            ]
            recording.events = new_events + recording.events
        return recording

    def calculate_optimal_fps(self, idle_time_limit: Optional[float] = None) -> float:
        min_delta: Optional[float] = None
        last: Optional[float] = None
        for event in self.events:
            if not isinstance(event, TerminalOutput):
                continue
            if last is None:
                last = event.time
            else:
                delta = event.time - last
                if idle_time_limit is not None and idle_time_limit > 0:
                    delta = min(delta, idle_time_limit)
                if delta >= 0.06:
                    if min_delta is None:
                        min_delta = delta
                    else:
                        min_delta = min(min_delta, delta)
                    last = event.time
        if min_delta is None or min_delta == 0.0:
            return 0
        else:
            return 1.0 / min_delta

    def screenshot(
            self,
            output_stream: BinaryIO,
            font: Union[FreeTypeFont, FontCollection],
            event_callback: Callable[[int, int], None] = lambda *_: None
    ):
        width = self.size.width
        height = self.size.height
        if width is None:
            width = 80
        if height is None:
            height = 24
        term = ANSITerminal(width, height, scrollback=None)
        n = len(self.events)
        for i, event in enumerate(self.events):
            event_callback(i, n)
            if not isinstance(event, TerminalOutput):
                continue
            term.write(event.data)
        term.render(font, include_scrollback=True).save(output_stream)

    def render(
            self,
            output_stream: BinaryIO,
            font: Union[FreeTypeFont, FontCollection],
            fps: Optional[float] = None,
            idle_time_limit: int = 0,
            loop: int = 0,
            frame_callback: Callable[[int, int], None] = lambda *_: None
    ):
        width = self.size.width
        height = self.size.height
        if width is None:
            width = 80
        if height is None:
            height = 24
        images = []
        if fps is None:
            fps = math.ceil(self.calculate_optimal_fps(idle_time_limit=idle_time_limit))
        num_frames: int = math.ceil(self.events[-1].time) * fps
        offset = 0
        term = ANSITerminal(width, height)
        if idle_time_limit is None or idle_time_limit <= 0:
            max_idle_frames = num_frames + 1
        else:
            max_idle_frames = int(idle_time_limit * fps + 0.5)
        idle_frames = 0
        for frame in range(num_frames + 1):
            frame_callback(frame, num_frames)

            frame_start = float(frame) / float(fps)
            frame_end = frame_start + 1.0 / float(fps)
            is_idle = True
            for event in self.events[offset:]:
                if not isinstance(event, TerminalOutput):
                    continue
                elif event.time >= frame_end:
                    break
                offset += 1
                is_idle = False
                term.write(event.data)
            if is_idle:
                idle_frames += 1
                if idle_frames >= max_idle_frames:
                    # drop this frame to stay within the idle_time_limit
                    continue
            else:
                idle_frames = 0

            images.append(term.render(font))

            term.bell = False

        images[0].save(output_stream, save_all=True,
                       append_images=images[1:],
                       duration=1000.0 / float(fps),
                       loop=loop)


R = TypeVar("R", bound=TerminalRecording)


class TerminalRecorder(Generic[R]):
    def __init__(self, recording: R, encoding: str = "utf-8"):
        self.recording: R = recording
        self.decoder = codecs.getincrementaldecoder(encoding)()

    def spawn(self, argv: Iterable[str]) -> int:
        """Create a spawned process."""
        if not isinstance(argv, list) and not isinstance(argv, tuple):
            argv = list(argv)
        sys.audit("pty.spawn", argv)
        pid, master_fd = pty.fork()
        if pid == pty.CHILD:
            # we are running in the child, so execute the process:
            os.execlp(argv[0], *argv)
            assert False  # this should never be reachable
        try:
            mode = termios.tcgetattr(pty.STDIN_FILENO)
            tty.setraw(pty.STDIN_FILENO)
            restore = True
        except termios.error:
            restore = False
            mode = 0
        try:

            fds = [master_fd, pty.STDIN_FILENO]
            while True:
                rfds, wfds, xfds = select(fds, [], [])
                if master_fd in rfds:
                    data = self.read(master_fd)
                    if not data:  # Reached EOF.
                        break
                    else:
                        os.write(pty.STDOUT_FILENO, data)
                if pty.STDIN_FILENO in rfds:
                    data = os.read(pty.STDIN_FILENO, 1024)
                    if not data:
                        fds.remove(pty.STDIN_FILENO)
                    else:
                        while data:
                            n = os.write(master_fd, data)
                            data = data[n:]

        except OSError:
            pass
        finally:
            if restore:
                termios.tcsetattr(pty.STDIN_FILENO, termios.TCSAFLUSH, mode)

        os.close(master_fd)
        return os.waitpid(pid, 0)[1]

    def read(self, fd: int, num_bytes: int = 255) -> bytes:
        data = os.read(fd, num_bytes)
        if not data:
            # close the decoder, which will throw an error if the stream was incomplete:
            try:
                new_term_text = self.decoder.decode(bytes(), True)
            except UnicodeDecodeError:
                sys.stderr.write("Warning: reached the end of the program output while decoding UTF-8; "
                                 "ignoring...\n")
                new_term_text = ""
            # we also have to close stdin, otherwise the pty will hang forever:
            sys.stdin.close()
        else:
            new_term_text = self.decoder.decode(data)
        if new_term_text:
            self.recording.events.append(TerminalOutput(data=new_term_text))
        return data

    def record(self, argv: Iterable[str]) -> R:
        retval = self.spawn(argv)
        self.recording.return_value = retval
        return self.recording
