from enum import IntEnum
import json
import math
import pkg_resources
from typing import (
    Any, BinaryIO, Callable, Dict, Iterable, List, Optional, SupportsInt, SupportsIndex, Tuple, Union
)

from PIL import Image, ImageDraw
from PIL.ImageFont import FreeTypeFont

from .screen import CGAAttribute, CGAColor, Screen, to_rgb

__version__: str = pkg_resources.require("cast2gif")[0].version
__version_name__: str = f"ToB/v{__version__}/source/Cast2Gif"


def to_int(n: Union[str, bytes, SupportsInt, SupportsIndex], default: Optional[int] = None) -> Optional[int]:
    try:
        return int(n)
    except (TypeError, ValueError):
        return default


def ansi_to_cga(index: int) -> CGAColor:
    """Converts ANSI X.364 to CGA"""
    index = index % 8
    return CGAColor([0, 4, 2, 6, 1, 5, 3, 7][index])


class ANSITerminal(Screen):
    """A simple ANSI terminal emulator"""
    class TerminalState(IntEnum):
        OUTSIDE = 0
        ESC = 1
        ESCBKT = 2
        OSC = 3

    def __init__(self, width: int, height: int):
        super().__init__(width, height)
        self._state: ANSITerminal.TerminalState = ANSITerminal.TerminalState.OUTSIDE
        self._esc: Optional[str] = None
        self._stored_pos: Optional[Tuple[int, int]] = None
        self._last_char: Optional[str] = None

    def write(self, char: Optional[str], foreground: Optional[CGAColor] = None, background: Optional[CGAColor] = None,
              attr: Optional[CGAAttribute] = None):
        if char is None or len(char) == 0 or char in '\x13\x14\x15\x26':
            pass
        elif len(char) > 1:
            for c in char:
                self.write(c, foreground=foreground, background=background, attr=attr)
        elif self._state == ANSITerminal.TerminalState.OUTSIDE:
            if ord(char) == 27:
                self._state = ANSITerminal.TerminalState.ESC
            else:
                super().write(char, foreground=foreground, background=background, attr=attr)
        elif self._state == ANSITerminal.TerminalState.ESC:
            self._write_esc(char)
        elif self._state == ANSITerminal.TerminalState.ESCBKT:
            self._write_escbkt(char)
        elif self._state == ANSITerminal.TerminalState.OSC:
            # an Operating System Command is terminated by the BEL character
            # or by ESC\
            if char == '\x07' or char == '\\' and ord(self._last_char) == 27:
                self._state = ANSITerminal.TerminalState.OUTSIDE
        self._last_char = char

    def _write_esc(self, char: str):
        if char == ']':
            self._state = ANSITerminal.TerminalState.OSC
        elif char == '[':
            self._state = ANSITerminal.TerminalState.ESCBKT
            self._esc = ''
        elif char in '\030\031':
            self._state = ANSITerminal.TerminalState.OUTSIDE
        else:
            raise Exception(f"Escape sequence ESC \\x{ord(char):02x} is not currently supported!")

    def _write_escbkt(self, char: str):
        esc_value = to_int(self._esc, 1)
        matched = True
        if char == 'A':
            self.move_up(esc_value)
        elif char in 'Be':
            self.move_down(esc_value)
        elif char in 'Ca':
            self.move_right(esc_value)
        elif char in 'D':
            self.move_left(esc_value)
        elif char in 'd`':
            self.move_to(0, esc_value - 1)
        elif char in 'E`':
            self.move_down(esc_value)
            self.write('\r')
        elif char in 'F`':
            self.move_up(esc_value)
            self.write('\r')
        elif char in 'G`':
            self.move_to(esc_value - 1)
        elif char == 'H':
            esc_value = self._esc.split(';')
            if len(esc_value) == 2:
                row, col = esc_value
            elif len(esc_value) == 1:
                row, col = esc_value[0], None
            else:
                row, col = None, None
            self.move_to(to_int(col, 1) - 1, to_int(row, 1) - 1)
        elif char == 'J':
            esc_value = to_int(self._esc, 0)
            self.clear(esc_value)
            if esc_value == 2:
                self.move_to(0, 0)
        elif char == 'K':
            esc_value = to_int(self._esc, 0)
            self.erase_line(esc_value)
        elif char == 'h':
            if self._esc == '?2004':
                # we don't need to handle bracketed paste mode
                pass
            else:
                raise Exception("ESC[%sh escape is currently unsupported!" % self._esc)
        elif char == 'l':
            if self._esc == '?2004':
                # we don't need to handle bracketed paste mode
                pass
            else:
                raise Exception("ESC[%sl escape is currently unsupported!" % self._esc)
        elif char == 'm':
            self._write_esc_m()
        elif char == 's':
            self._stored_pos = (self.col, self.row)
        elif char == 'u':
            if self._stored_pos is not None:
                self.move_to(*self._stored_pos)
        elif char in 'STfinhl':
            raise Exception(f"ESC[{self._esc}{char} escape is currently unsupported!")
        else:
            matched = False
        if matched:
            self._state = ANSITerminal.TerminalState.OUTSIDE
        self._esc += char

    def _write_esc_m(self):
        for esc in map(to_int, self._esc.split(';')):
            if esc is None:
                continue
            elif esc == 0:
                self.foreground = CGAColor.GRAY
                self.background = CGAColor.BLACK
                self.attr = CGAAttribute.PLAIN
            elif esc == 1:
                self.foreground |= CGAAttribute.INTENSE
            elif esc in [2, 21, 22]:
                self.foreground |= ~CGAAttribute.INTENSE
            elif esc == 5:
                self.background |= CGAAttribute.INTENSE
            elif esc == 7:
                self.attr |= CGAAttribute.INVERSE
            elif esc == 25:
                self.background &= ~CGAAttribute.INTENSE
            elif esc == 27:
                self.attr &= ~CGAAttribute.INVERSE
            elif esc in range(30, 38):
                self.foreground = (self.foreground & CGAAttribute.INTENSE) | ansi_to_cga(esc - 30)
            elif esc in range(40, 48):
                self.background = (self.background & CGAAttribute.INTENSE) | ansi_to_cga(esc - 40)
            elif esc in range(90, 98):
                self.foreground = ansi_to_cga(esc - 82)
            elif esc in range(100, 108):
                self.foreground = ansi_to_cga(esc - 92)


class AsciiCast:
    def __init__(self, cast: Union[bytes, str, Iterable[str]], width: int = None, height: int = None):
        if isinstance(cast, str) or isinstance(cast, bytes):
            cast = cast.splitlines()
        self.metadata: Dict[str, Any] = {}
        self.data: List[Tuple[float, str, str]] = []
        for i, line in enumerate(cast):
            if i == 0:
                self.metadata = json.loads(line)
            else:
                self.data.append(json.loads(line))
        if width is not None:
            self.metadata["width"] = width
        if height is not None:
            self.metadata["height"] = height

    def calculate_optimal_fps(self, idle_time_limit: Optional[float] = None) -> float:
        min_delta: Optional[float] = None
        last: Optional[float] = None
        for time, event_type, data in self.data:
            if event_type == 'o':
                if last is None:
                    last = time
                else:
                    delta = time - last
                    if idle_time_limit is not None and idle_time_limit > 0:
                        delta = min(delta, idle_time_limit)
                    if delta >= 0.06:
                        if min_delta is None:
                            min_delta = delta
                        else:
                            min_delta = min(min_delta, delta)
                        last = time
        if min_delta is None or min_delta == 0.0:
            return 0
        else:
            return 1.0 / min_delta

    def render(
            self,
            output_stream: BinaryIO,
            font: FreeTypeFont,
            fps: Optional[float] = None,
            idle_time_limit: int = 0,
            loop: int = 0,
            frame_callback: Optional[Callable[[int, int], None]] = None
    ):
        font_width, font_height = font.getsize('X')
        width = self.metadata["width"]
        height = self.metadata["height"]
        image_width = width * font_width
        image_height = height * font_height
        images = []
        if fps is None:
            fps = math.ceil(self.calculate_optimal_fps(idle_time_limit=idle_time_limit))
        num_frames: int = math.ceil(self.data[-1][0]) * fps
        offset = 0
        term = ANSITerminal(width, height)
        if idle_time_limit is None or idle_time_limit <= 0:
            max_idle_frames = num_frames + 1
        else:
            max_idle_frames = int(idle_time_limit * fps + 0.5)
        idle_frames = 0
        for frame in range(num_frames + 1):
            if frame_callback is not None:
                frame_callback(frame, num_frames)
            im = Image.new('RGB', (image_width + 2 * font_width, image_height + 2 * font_height))
            images.append(im)
            draw = ImageDraw.Draw(im)
            frame_start = float(frame) / float(fps)
            frame_end = frame_start + 1.0 / float(fps)
            is_idle = True
            for time, event_type, data in self.data[offset:]:
                if event_type != 'o':
                    continue
                elif time >= frame_end:
                    break
                offset += 1
                is_idle = False
                term.write(data)
            if is_idle:
                idle_frames += 1
                if idle_frames >= max_idle_frames:
                    # drop this frame to stay within the idle_time_limit
                    continue
            else:
                idle_frames = 0
            if term.bell:
                fill_color = term.foreground
            else:
                fill_color = term.background
            draw.rectangle(
                ((0, 0), (image_width + 2 * font_width, image_height + 2 * font_height)),
                fill=to_rgb(fill_color)
            )
            cursor_drawn = False
            for y, r in enumerate(term.screen):
                for x, cell in enumerate(r):
                    if cell is not None:
                        c, foreground, background, attr = cell.value, cell.foreground, cell.background, cell.attr
                        if term.bell:
                            foreground, background = background, foreground
                        if int(CGAAttribute.INVERSE) & int(attr):
                            foreground, background = background, foreground
                        if not term.hide_cursor and term.row == y and term.col == x:
                            foreground, background = background, foreground
                            cursor_drawn = True
                        pos = (font_width * (x + 1), font_height * (y + 1))
                        draw.rectangle((pos, (pos[0] + font_width + 1, pos[1] + 1)), fill=to_rgb(background))
                        draw.text((pos[0], pos[1]), c, fill=to_rgb(foreground), font=font)
            if not term.hide_cursor and not cursor_drawn:
                pos = (font_width * (term.col + 1) + 1, font_height * (term.row + 1) + 1)
                draw.rectangle(((pos[0], pos[1] + font_height), (pos[0] + font_width, pos[1])), fill=to_rgb(term.foreground))
            term.bell = False

        images[0].save(output_stream, save_all=True,
                       append_images=images[1:],
                       duration=1000.0 / float(fps),
                       loop=loop)
