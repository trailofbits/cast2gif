VERSION='0.0.1'
VERSION_NAME="ToB/v%s/source/AsciiCast2Gif" % VERSION

from enum import Enum
import json
import math

from PIL import Image, ImageDraw

def constrain(n, n_min, n_max):
    '''Constrain n to the range [n_min, n_max)'''
    return min(max(n, n_min), n_max - 1)

def to_int(n, default=None):
    try:
        return int(n)
    except (TypeError, ValueError):
        return default

def numeric_enum(c):
    def __and__(self, n):
        if isinstance(n, Enum):
            n = n.value
        return EnumAwareInt(int(self.value) & int(n))
    def __or__(self, n):
        if isinstance(n, Enum):
            n = n.value
        return EnumAwareInt(int(self.value) | int(n))
    def __invert__(self):
        return EnumAwareInt(~int(self.value))
    def __int__(self):
        return self.value
    setattr(c, '__and__', __and__)
    setattr(c, '__or__', __or__)
    setattr(c, '__invert__', __invert__)
    setattr(c, '__int__', __int__)
    return c

@numeric_enum
class EnumAwareInt(object):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return str(self.value)
    def __repr__(self):
        return "EnumAwareInt<%d>" % int(self.value)

@numeric_enum
class CGAColor(Enum):
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

def to_rgb(color):
    value = color.value & 0b1111 # Strip out the high attribute bits
    if value == int(CGAColor.BLACK):
        return (0, 0, 0)
    elif value == int(CGAColor.BLUE):
        return (0, 0, 255)
    elif value == int(CGAColor.GREEN):
        return (0, 255, 0)
    elif value == int(CGAColor.CYAN):
        return (0, 255, 255)
    elif value == int(CGAColor.RED):
        return (255, 0, 0)
    elif value == int(CGAColor.MAGENTA):
        return (0xAA, 0x00, 0xAA)
    elif value == int(CGAColor.BROWN):
        return (0xAA, 0x55, 0x00)
    elif value == int(CGAColor.GRAY):
        return (0xAA,) * 3
    elif value == int(CGAColor.DARK_GRAY):
        return (0x55,) * 3
    elif value == int(CGAColor.LIGHT_BLUE):
        return (0x55, 0x55, 0xFF)
    elif value == int(CGAColor.LIGHT_GREEN):
        return (0x55, 0xFF, 0x55)
    elif value == int(CGAColor.LIGHT_CYAN):
        return (0x55, 0xFF, 0xFF)
    elif value == int(CGAColor.LIGHT_RED):
        return (0xFF, 0x55, 0x55)
    elif value == int(CGAColor.LIGHT_MAGENTA):
        return (0xFF, 0x55, 0xFF)
    elif value == int(CGAColor.YELLOW):
        return (0xFF, 0xFF, 0x55)
    elif value == int(CGAColor.WHITE):
        return (255, 255, 255)
    else:
        raise Exception("Unsupported Color: %s (value = %d)" % (color, color.value))

def ansi_to_cga(index):
    '''Converts ANSI X.364 to CGA'''
    index = index % 8
    return CGAColor([0, 4, 2, 6, 1, 5, 3, 7][index])

@numeric_enum
class CGAAttribute(Enum):
    PLAIN = 0
    INVERSE = 1
    INTENSE = 8

class Screen(object):
    def __init__(self, width, height):
        self.col = 0
        self.row = 0
        self.width = width
        self.height = height
        self.screen = None
        self.foreground = CGAColor.GRAY
        self.background = CGAColor.BLACK
        self.attr = CGAAttribute.PLAIN
        self.bell = False
        self.hide_cursor = False
        self.clear(2)

    def clear(self, screen_portion=0):
        '''
        Clears a portion or all of the screen

        :param screen_portion: 0 (default) clears from cursor to end of screen; 1 clears from cursor to the beginning of the screen; and 2 clears the entire screen
        :return: returns nothing
        '''
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

    def erase_line(self, line_portion=0):
        '''
        Clears a portion or all of the current line

        :param line_portion: 0 (default) clears from cursor to end of line; 1 clears from cursor to the beginning of the line; and 2 clears the entire line
        :return: returns nothing
        '''
        if line_portion == 1:
            # Clear from the beginning of the line to the cursor
            self.screen[self.row] = [None] * (self.width - self.col + 1) + self.screen[self.row][self.col + 1:]
        elif line_portion == 2:
            # Clear the entire line
            self.screen[self.row] = [None] * self.width
        else:
            # Clear from the cursor to the end of the line
            self.screen[self.row] = self.screen[self.row][:self.col] + [None] * (self.width - self.col)
            
    def write(self, char, foreground = None, background = None, attr = None):
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
            if self.row >= 0 and self.row < self.height and self.col >= 0 and self.col < self.width:
                self.screen[self.row][self.col] = (char, foreground, background, attr)
            self.col += 1
        if self.col >= self.width:
            self.col = 0
            self.row += 1
        if self.row >= self.height:
            extra_rows = self.row - self.height + 1
            self.screen = self.screen[extra_rows:] + [[None] * self.width for i in range(extra_rows)]
            self.row = self.height - 1

    def move_up(self, rows=1):
        self.row = constrain(self.row - rows, 0, self.height)

    def move_down(self, rows=1):
        self.row = constrain(self.row + rows, 0, self.height)

    def move_left(self, cols=1):
        self.col = constrain(self.col - cols, 0, self.width)

    def move_right(self, cols=1):
        self.col = constrain(self.col + cols, 0, self.width)

    def move_to(self, col = None, row = None):
        if col is not None:
            self.col = col
        if row is not None:
            self.row = row

class ANSITerminal(Screen):
    '''A simple ANSI terminal emulator'''
    class TerminalState(Enum):
        OUTSIDE = 0
        ESC = 1
        ESCBKT = 2
        OSC = 3

    def __init__(self, width, height):
        super().__init__(width, height)
        self._state = ANSITerminal.TerminalState.OUTSIDE
        self._esc = None
        self._stored_pos = None
        self._last_char = None

    def write(self, char):
        if char is None or len(char) == 0 or char in '\x13\x14\x15\x26':
            pass
        elif len(char) > 1:
            for c in char:
                self.write(c)
        elif self._state == ANSITerminal.TerminalState.OUTSIDE:
            if ord(char) == 27:
                self._state = ANSITerminal.TerminalState.ESC
            else:
                super().write(char)
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

    def _write_esc(self, char):
        if char == ']':
            self._state = ANSITerminal.TerminalState.OSC
        elif char == '[':
            self._state = ANSITerminal.TerminalState.ESCBKT
            self._esc = ''
        elif char in '\030\031':
            self._state = ANSITerminal.TerminalState.OUTSIDE
        else:
            raise Exception("Escape sequence ESC \\x%x is not currently supported!" % ord(char))

    def _write_escbkt(self, char):
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
            raise Exception("ESC[%s%s escape is currently unsupported!" % (self._esc, char))
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

class AsciiCast(object):
    def __init__(self, cast, width=None, height=None):
        self.metadata = None
        self.data = []
        for line in cast.splitlines():
            if self.metadata is None:
                self.metadata = json.loads(line)
            else:
                self.data.append(json.loads(line))
        if width is not None:
            self.metadata['width'] = width
        if height is not None:
            self.metadata['height'] = height
    def calculate_optimal_fps(self, idle_time_limit = None):
        min_delta = None
        last = None
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
    def render(self, output_stream, font, fps = None, idle_time_limit = 0, loop = 0, frame_callback = None):
        font_width, font_height = font.getsize('X')
        width = self.metadata['width']
        height = self.metadata['height']
        image_width = width * font_width
        image_height = height * font_height
        images = []
        if fps is None:
            fps = math.ceil(self.calculate_optimal_fps(idle_time_limit = idle_time_limit))
        num_frames = math.ceil(self.data[-1][0]) * fps
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
            draw.rectangle(((0, 0), (image_width + 2 * font_width, image_height + 2 * font_height)), fill=to_rgb(fill_color))
            cursor_drawn = False
            for y, r in enumerate(term.screen):
                for x, cell in enumerate(r):
                    if cell is not None:
                        c, foreground, background, attr = cell
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
