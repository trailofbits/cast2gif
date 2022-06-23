from enum import IntEnum, IntFlag
import itertools
from typing import Iterable, List, Optional, Tuple, TypeVar, Union

from PIL import Image, ImageDraw, ImageFont
from PIL.ImageFont import FreeTypeFont

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
    def __init__(self, width: int, height: int, scrollback: Optional[int] = 0):
        self.col: int = 0
        self.row: int = 0
        self.width: int = width
        self.height: int = height
        self.scrollback: Optional[int] = scrollback
        self.scroll_buffer: List[List[Optional[ScreenCell]]] = []
        self.screen: List[List[Optional[ScreenCell]]] = []
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
            self.screen = [[None] * self.width for _ in range(self.row)] + self.screen[self.row:]
        elif screen_portion == 2:
            # Clear the entire screen
            self.screen = [[None] * self.width for _ in range(self.height)]
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
            if extra_rows > 0 and (self.scrollback is None or self.scrollback > 0):
                self.scroll_buffer += self.screen[:extra_rows]
                if self.scrollback is not None:
                    self.scroll_buffer = self.scroll_buffer[-self.scrollback:]
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

    def render(self, font: FreeTypeFont, include_scrollback: bool = False, antialias: bool = True) -> Image:
        if antialias:
            scale_factor = 2
            font = ImageFont.truetype(font=font.path, size=font.size * scale_factor)
            # desired_width = font_width * scale_factor
            # desired_height = font_height * scale_factor
            # while True:
            #     font = ImageFont.truetype(font=font.path, size=font.size + 1)
            #     font_width, font_height = font.getsize('X')
            #     if font_width >= desired_width and font_height >= desired_height:
            #         break
        else:
            scale_factor = 1
        font_width, font_height = font.getsize('X')
        image_width = self.width * font_width
        image_height = self.height * font_height
        if include_scrollback:
            image_height += len(self.scroll_buffer) * font_height
        im = Image.new("RGB", (image_width + 2 * font_width, image_height + 2 * font_height))
        draw = ImageDraw.Draw(im)
        if self.bell:
            fill_color = self.foreground
        else:
            fill_color = self.background
        draw.rectangle(
            ((0, 0), (image_width + 2 * font_width, image_height + 2 * font_height)),
            fill=to_rgb(fill_color)
        )
        cursor_drawn = False
        if include_scrollback:
            data: Iterable[List[Optional[ScreenCell]]] = itertools.chain(self.scroll_buffer, self.screen)
        else:
            data = self.screen
        for y, r in enumerate(data):
            for x, cell in enumerate(r):
                if cell is not None:
                    c, foreground, background, attr = cell.value, cell.foreground, cell.background, cell.attr
                    if self.bell:
                        foreground, background = background, foreground
                    if int(CGAAttribute.INVERSE) & int(attr):
                        foreground, background = background, foreground
                    if not self.hide_cursor and self.row == y and self.col == x:
                        foreground, background = background, foreground
                        cursor_drawn = True
                    pos = (font_width * (x + 1), font_height * (y + 1))
                    draw.rectangle((pos, (pos[0] + font_width + 1, pos[1] + 1)), fill=to_rgb(background))
                    draw.text((pos[0], pos[1]), c, fill=to_rgb(foreground), font=font)

        if not self.hide_cursor and not cursor_drawn:
            pos = (font_width * (self.col + 1) + 1, font_height * (self.row + 1) + 1)
            draw.rectangle(
                ((pos[0], pos[1] + font_height), (pos[0] + font_width, pos[1])),
                fill=to_rgb(self.foreground)
            )

        if antialias:
            im = im.resize((image_width // scale_factor, image_height // scale_factor), resample=Image.ANTIALIAS)

        return im
