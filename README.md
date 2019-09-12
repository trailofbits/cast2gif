# Cast2Gif
An pure Python ANSI terminal emulator that can render AsciiCast terminal recordings to an animated GIF. 

## Quickstart

In the same directory as this README, run:
```
pip3 install .
```

This will automatically install the `cast2gif` executable in your path.

## Usage

```
usage: cast2gif [-h] [-v] [-o OUTPUT] [--force] [--font FONT] [-s FONT_SIZE]
                [--fps FPS] [--idle-time-limit IDLE_TIME_LIMIT] [--loop LOOP]
                [--quiet] [--width WIDTH] [--height HEIGHT]
                ASCIICAST

Converts AsciiCast terminal recordings to animated GIFs

positional arguments:
  ASCIICAST             The AsciiCast v2 file to convert, or '-' for STDIN

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         Print version information and exit
  -o OUTPUT, --output OUTPUT
                        The path for the output GIF file, or '-' for STDOUT
                        (default is the input filename plus '.gif', or STDOUT
                        if the input file is STDIN)
  --force               Overwrite the output file even if it already exists
  --font FONT           Path to a TrueType font for rendering; defaults to
                        SourceCodePro
  -s FONT_SIZE, --font-size FONT_SIZE
                        Font size (default=12)
  --fps FPS             Speficy the number of frames per second in the output
                        GIF; by default, an optimal FPS is calculated
  --idle-time-limit IDLE_TIME_LIMIT
                        The maximum amount of idle time that can occur between
                        terminal events; by default this is read from the
                        AsciiCast input, or set to zero if none is specified
                        in the input; if provided, this option will override
                        whatever is specified in the input
  --loop LOOP           The number of times the GIF should loop, or zero if it
                        should loop forever (default=0)
  --quiet               Suppress all logging and status printouts
  --width WIDTH         Override the output width
  --height HEIGHT       Override the output height
```

## License

Cast2Gif is licensed and distributed under the [AGPLv3](LICENSE) license. [Contact us](mailto:opensource@trailofbits.com) if you’re looking for an exception to the terms.
