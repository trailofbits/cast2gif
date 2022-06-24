from pathlib import Path
import os
from setuptools import setup, find_packages

SCRIPT_PATH = Path(__file__).absolute().parent
PKG_DIR = SCRIPT_PATH / "cast2gif"
FONT_DIR = PKG_DIR / "fonts"
FONT_FILES = [str(f.relative_to(PKG_DIR)) for f in FONT_DIR.glob("**/*") if f.is_file() and not f.name.startswith(".")]

setup(
    name="cast2gif",
    description="Converts AsciiCast terminal recordings to animated GIFs",
    url="https://github.com/trailofbits/cast2gif",
    author="Trail of Bits",
    version="0.0.3",
    packages=find_packages(),
    package_data={"cast2gif": FONT_FILES},
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=["fonttools>=4.33.3", "Pillow>=5.3.0"],
    entry_points={"console_scripts": ["cast2gif = cast2gif.__main__:main"]},
)
