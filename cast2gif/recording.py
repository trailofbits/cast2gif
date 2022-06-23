import codecs
import math
import os
import pty
from select import select
import sys
import termios
import time as time_module
import tty
from typing import BinaryIO, Callable, Generic, Iterable, List, Optional, Type, TypeVar

from PIL.ImageFont import FreeTypeFont

from .terminal import ANSITerminal


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


class TerminalRecording:
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
        self.width: Optional[int] = width
        self.height: Optional[int] = height
        self.return_value: Optional[int] = None
        self.events: List[TerminalEvent] = []

    @classmethod
    def record(cls: Type[C], argv: Iterable[str], encoding: str = "utf-8") -> C:
        return TerminalRecorder(recording_type=cls, encoding=encoding).record(argv)

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
            font: FreeTypeFont,
            event_callback: Callable[[int, int], None] = lambda *_: None
    ):
        width = self.width
        height = self.height
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
            font: FreeTypeFont,
            fps: Optional[float] = None,
            idle_time_limit: int = 0,
            loop: int = 0,
            frame_callback: Callable[[int, int], None] = lambda *_: None
    ):
        width = self.width
        height = self.height
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
    def __init__(self, recording_type: Type[R] = TerminalRecording, encoding: str = "utf-8"):
        self.recording_type: Type[R] = recording_type
        self.recording: Optional[R] = None
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
        if self.recording is None:
            try:
                term_size = os.get_terminal_size(fd)
                if term_size.columns > 0 and term_size.lines > 0:
                    width, height = term_size.columns, term_size.lines
                else:
                    width, height = None, None
            except OSError:
                width, height = None, None
            self.recording = self.recording_type(width, height)

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
        if self.recording is None:
            recording = self.recording_type()
            recording.return_value = retval
            return recording
        else:
            self.recording.return_value = retval
            return self.recording
