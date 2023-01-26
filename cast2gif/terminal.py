from enum import IntEnum
from typing import Optional, SupportsIndex, SupportsInt, Tuple, Union

from cast2gif.screen import Screen, CGAColor, CGAAttribute


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

    def __init__(self, width: int, height: int, scrollback: Optional[int] = 0):
        super().__init__(width, height, scrollback=scrollback)
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
                raise NotImplementedError("ESC[%sh escape is currently unsupported!" % self._esc)
        elif char == 'l':
            if self._esc == '?2004':
                # we don't need to handle bracketed paste mode
                pass
            else:
                raise NotImplementedError("ESC[%sl escape is currently unsupported!" % self._esc)
        elif char == 'm':
            self._write_esc_m()
        elif char == 's':
            self._stored_pos = (self.col, self.row)
        elif char == 'u':
            if self._stored_pos is not None:
                self.move_to(*self._stored_pos)
        elif char in 'STfinhl':
            raise NotImplementedError(f"ESC[{self._esc}{char} escape is currently unsupported!")
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


class NullScreen:
    def __getitem__(self, item) -> "NullScreen":
        return NullScreen()

    def __setitem__(self, key, value):
        pass

    def __add__(self, other):
        return NullScreen()


class InfiniteWidthTerminal(ANSITerminal):
    def __init__(self):
        self._col: int = 0
        self.maximum_width: int = 0
        super().__init__(width=99999999999999999999, height=99999999999999999999, scrollback=0)
        self.screen = NullScreen()  # type: ignore

    @property
    def col(self) -> int:
        return self._col

    @col.setter
    def col(self, new_value: int):
        self._col = new_value
        self.maximum_width = max(self.maximum_width, new_value)

    def clear(self, *args, **kwargs):
        pass

    def erase_line(self, line_portion: int = 0):
        pass
