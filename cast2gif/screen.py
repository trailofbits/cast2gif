from enum import IntEnum, IntFlag
from typing import List, Optional, Tuple, TypeVar, Union

T = TypeVar("T")


def constrain(n: T, n_min: T, n_max: T) -> T:
    """Constrain n to the range [n_min, n_max)"""
    return min(max(n, n_min), n_max - 1)


class CGAColor(IntEnum):
    BLACK = 0
    BLUE = 1
    GREEN = 2
    CYAN = 3
    RED = 4
    MAGENTA = 5
    BROWN = 6
    GRAY = 7

    DARK_GRAY = 8
    LIGHT_BLUE = 9
    LIGHT_GREEN = 10
    LIGHT_CYAN = 11
    LIGHT_RED = 12
    LIGHT_MAGENTA = 13
    YELLOW = 14
    WHITE = 15


def to_rgb(color: Union[int, CGAColor]) -> Tuple[int, int, int]:
    value = color & 0b1111  # Strip out the high attribute bits
    if value == int(CGAColor.BLACK):
        return 0, 0, 0
    elif value == int(CGAColor.BLUE):
        return 0, 0, 255
    elif value == int(CGAColor.GREEN):
        return 0, 255, 0
    elif value == int(CGAColor.CYAN):
        return 0, 255, 255
    elif value == int(CGAColor.RED):
        return 255, 0, 0
    elif value == int(CGAColor.MAGENTA):
        return 0xAA, 0x00, 0xAA
    elif value == int(CGAColor.BROWN):
        return 0xAA, 0x55, 0x00
    elif value == int(CGAColor.GRAY):
        return (0xAA,) * 3
    elif value == int(CGAColor.DARK_GRAY):
        return (0x55,) * 3
    elif value == int(CGAColor.LIGHT_BLUE):
        return 0x55, 0x55, 0xFF
    elif value == int(CGAColor.LIGHT_GREEN):
        return 0x55, 0xFF, 0x55
    elif value == int(CGAColor.LIGHT_CYAN):
        return 0x55, 0xFF, 0xFF
    elif value == int(CGAColor.LIGHT_RED):
        return 0xFF, 0x55, 0x55
    elif value == int(CGAColor.LIGHT_MAGENTA):
        return 0xFF, 0x55, 0xFF
    elif value == int(CGAColor.YELLOW):
        return 0xFF, 0xFF, 0x55
    elif value == int(CGAColor.WHITE):
        return 255, 255, 255
    else:
        raise Exception(f"Unsupported Color: {color} (value = {value})")


class CGAAttribute(IntFlag):
    PLAIN = 0
    INVERSE = 1
    INTENSE = 8


class ScreenCell:
    def __init__(self, value: str, foreground: CGAColor, background: CGAColor, attr: CGAAttribute):
        self.value: str = value
        self.foreground: CGAColor = foreground
        self.background: CGAColor = background
        self.attr: CGAAttribute = attr


class ScreenPortion(IntEnum):
    CURSOR_TO_END_OF_SCREEN = 0
    CURSOR_TO_BEGINNING_OF_SCREEN = 1
    ENTIRE_SCREEN = 2


class Screen:
    def __init__(self, width: int, height: int):
        self.col: int = 0
        self.row: int = 0
        self.width: int = width
        self.height: int = height
        self.screen: Optional[List[List[Optional[ScreenCell]]]] = None
        self.foreground: CGAColor = CGAColor.GRAY
        self.background: CGAColor = CGAColor.BLACK
        self.attr: CGAAttribute = CGAAttribute.PLAIN
        self.bell = False
        self.hide_cursor = False
        self.clear(2)

    def clear(self, screen_portion: Union[int, ScreenPortion] = ScreenPortion.CURSOR_TO_END_OF_SCREEN):
        """
        Clears a portion or all of the screen

        :param screen_portion: 0 (default) clears from cursor to end of screen; 1 clears from cursor to the beginning of
               the screen; and 2 clears the entire screen
        :return: returns nothing
        """
        if screen_portion == 1:
            # Clear from the beginning of the screen to the cursor
            self.screen[self.row] = [None] * (self.width - self.col + 1) + self.screen[self.row][self.col + 1:]
            self.screen = [[None] * self.width for i in range(self.row)] + self.screen[self.row:]
        elif screen_portion == 2:
            # Clear the entire screen
            self.screen = [[None] * self.width for i in range(self.height)]
        else:
            # Clear from the cursor to the end of the screen
            self.screen[self.row] = self.screen[self.row][:self.col] + [None] * (self.width - self.col)
            self.screen = self.screen[:self.row + 1] + [[None] * self.width for i in range(self.height - self.row - 1)]

    def erase_line(self, line_portion: int = 0):
        """
        Clears a portion or all of the current line

        :param line_portion: 0 (default) clears from cursor to end of line; 1 clears from cursor to the beginning of the
               line; and 2 clears the entire line
        :return: returns nothing
        """
        if line_portion == 1:
            # Clear from the beginning of the line to the cursor
            self.screen[self.row] = [None] * (self.width - self.col + 1) + self.screen[self.row][self.col + 1:]
        elif line_portion == 2:
            # Clear the entire line
            self.screen[self.row] = [None] * self.width
        else:
            # Clear from the cursor to the end of the line
            self.screen[self.row] = self.screen[self.row][:self.col] + [None] * (self.width - self.col)

    def write(self, char: Optional[str], foreground: Optional[CGAColor] = None, background: Optional[CGAColor] = None,
              attr: Optional[CGAAttribute] = None):
        if char is None:
            return
        elif char == '\n':
            self.col = 0
            self.row += 1
        elif char == '\r':
            self.col = 0
        elif char == '\b':
            # backspace
            if self.col > 0:
                self.screen[self.row] = self.screen[self.row][:self.col - 1] + self.screen[self.row][self.col:] + [None]
                self.col -= 1
        elif ord(char) == 127:
            # delete
            self.screen[self.row] = self.screen[self.row][:self.col] + self.screen[self.row][self.col + 1:] + [None]
        elif char == '\x07':
            self.bell = True
        else:
            if foreground is None:
                foreground = self.foreground
            if background is None:
                background = self.background
            if attr is None:
                attr = self.attr
            if 0 <= self.row < self.height and 0 <= self.col < self.width:
                self.screen[self.row][self.col] = ScreenCell(char, foreground, background, attr)
            self.col += 1
        if self.col >= self.width:
            self.col = 0
            self.row += 1
        if self.row >= self.height:
            extra_rows = self.row - self.height + 1
            self.screen = self.screen[extra_rows:] + [[None] * self.width for _ in range(extra_rows)]
            self.row = self.height - 1

    def move_up(self, rows: int = 1):
        self.row = constrain(self.row - rows, 0, self.height)

    def move_down(self, rows: int = 1):
        self.row = constrain(self.row + rows, 0, self.height)

    def move_left(self, cols: int = 1):
        self.col = constrain(self.col - cols, 0, self.width)

    def move_right(self, cols: int = 1):
        self.col = constrain(self.col + cols, 0, self.width)

    def move_to(self, col: Optional[int] = None, row: Optional[int] = None):
        if col is not None:
            self.col = col
        if row is not None:
            self.row = row
