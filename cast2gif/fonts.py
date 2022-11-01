from functools import lru_cache
from pathlib import Path
from typing import List, Iterator, Optional, Sequence, Tuple, Union

from PIL import ImageFont
from PIL.ImageFont import FreeTypeFont
from fontTools.ttLib import TTFont

from .sets import OrderedMutableSet


class FontCollection:
    def __init__(self, *fonts: Union[str, Path, FreeTypeFont, TTFont], size: int):
        self.size: int = size
        self._fonts: List[FreeTypeFont] = []
        self._ttfonts: List[TTFont] = []
        for font in fonts:
            self.add(font)

    def __iter__(self) -> Iterator[FreeTypeFont]:
        return iter(self._fonts)

    def __len__(self):
        return len(self._fonts)

    def __getitem__(self, index: int) -> FreeTypeFont:
        return self._fonts[index]

    def with_size(self, size: int) -> "FontCollection":
        return FontCollection(*self._fonts, size=size)

    @property
    def fonts(self) -> Sequence[FreeTypeFont]:
        return self._fonts

    def add(self, font: Union[str, Path, FreeTypeFont]):
        if isinstance(font, FreeTypeFont):
            if any(f.path == font.path for f in self._fonts):
                # we already added this font
                return
            if font.size != self.size:
                font = ImageFont.truetype(font=font.path, size=self.size)
            self._fonts.append(font)
            self._ttfonts.append(TTFont(font.path))
        else:
            font = str(Path(font).expanduser().absolute())
            if any(f.path == font for f in self._fonts):
                # we already added this font
                return
            self._fonts.append(ImageFont.truetype(font=font, size=self.size))
            self._ttfonts.append(TTFont(font))

    @lru_cache(maxsize=1024)
    def fonts_satisfying(self, text: str) -> OrderedMutableSet[FreeTypeFont]:
        """Returns the set of fonts that satisfy every glyph in the text"""
        if len(text) == 0:
            return OrderedMutableSet(self.fonts)
        if len(text) > 1:
            fonts: OrderedMutableSet[FreeTypeFont] = OrderedMutableSet(self.fonts)
            for c in text:
                fonts &= self.fonts_satisfying(c)
                if not fonts:
                    return fonts
            return fonts
        # len(text) == 1 here
        fonts = OrderedMutableSet()
        for font, ttfont in zip(self._fonts, self._ttfonts):
            for table in ttfont["cmap"].tables:
                if ord(text) in table.cmap.keys():
                    fonts.add(font)
        return fonts

    @lru_cache(maxsize=1024)
    def getsize(self, for_text: str) -> Tuple[int, int]:
        return self.get_font(for_text).getsize(for_text)

    def get_font(self, for_text: str) -> Optional[FreeTypeFont]:
        try:
            return next(iter(self.fonts_satisfying(for_text)))
        except StopIteration:
            try:
                return next(iter(self.fonts))
            except StopIteration:
                return None
