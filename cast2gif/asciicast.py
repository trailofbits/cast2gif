import json
import math
import pkg_resources
from typing import Any, BinaryIO, Callable, Dict, Iterable, List, Optional, Tuple, Union

from PIL import Image, ImageDraw
from PIL.ImageFont import FreeTypeFont

from .screen import CGAAttribute, to_rgb
from .terminal import ANSITerminal

__version__: str = pkg_resources.require("cast2gif")[0].version
__version_name__: str = f"ToB/v{__version__}/source/Cast2Gif"


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
