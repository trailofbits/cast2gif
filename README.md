# Cast2Gif
A pure Python ANSI terminal emulator that can render AsciiCast terminal recordings to an animated GIF or screenshot.

Cast2Gif can also generate its own recordings directly, without requiring asciinema to be installed (see the `--exec` option).

For example, to generate a PNG screenshot of the output of the `ls` command, run
```bash
cast2gif --screenshot --output ls.png  --exec  "ls"
```

## Quickstart

In the same directory as this README, run:
```
pip3 install .
```

This will automatically install the `cast2gif` executable in your path.

## Usage

```
usage: cast2gif [-h] [-v] [--exec ...] [--hide-prompt] [--ps1 PS1] [-o OUTPUT]
                [--force] [--screenshot] [--font FONT] [-s FONT_SIZE]
                [--fps FPS] [--idle-time-limit IDLE_TIME_LIMIT] [--loop LOOP]
                [--quiet] [--width WIDTH] [--height HEIGHT] [--auto-size]
                [ASCIICAST]

Converts AsciiCast terminal recordings to animated GIFs

positional arguments:
  ASCIICAST             The AsciiCast v2 file to convert, or '-' for STDIN
                        (the default)

options:
  -h, --help            show this help message and exit
  -v, --version         Print version information and exit
  --exec ..., -c ...    Instead of parsing an AsciiCast v2 file, run the
                        command immediately after `--exec` and use its output
  --hide-prompt         By default, when using the `--exec` argument to run a
                        command, the command prompt is included before the
                        command output; this argument hides the prompt and
                        only includes the output
  --ps1 PS1             The PS1 command prompt to use in conjuction with the
                        `--exec` output (default="${PS1}", if it is set,
                        otherwise "$ " in green)
  -o OUTPUT, --output OUTPUT
                        The path for the output GIF file, or '-' for STDOUT
                        (default is the input filename plus '.gif', or STDOUT
                        if the input file is STDIN)
  --force               Overwrite the output file even if it already exists
  --screenshot, -sc     Render a screenshot rather than an animated gif
  --font FONT           Path to a TrueType font for rendering; defaults to
                        SourceCodePro; this argument can be supplied multiple
                        times, with additional fonts used in the event that
                        one is missing a required glyph
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
  --auto-size           Override the output dimensions to be wide enough to
                        fit every line; if specified, this overrides the
                        `--width` option
```

## License

Cast2Gif is licensed and distributed under the [AGPLv3](LICENSE) license. [Contact us](mailto:opensource@trailofbits.com) if you’re looking for an exception to the terms.

Several fonts are distributed with Cast2Gif. They are licensed as follows:
- **Fira Code Nerd Font**: Copyright © 2014, The Fira Code Project Authors and distributed under the
  [SIL Open Font License, Version 1.1](cast2gif/fonts/FiraCode/LICENSE)
- **Hack Nerd Font**: Copyright © 2018, Source Foundry Authors and distributed under the
  [MIT License](cast2gif/fonts/Hack/LICENSE.md)
- **Adobe SourceCodePro**: Copyright © 2010, 2012 Adobe Systems Incorporated and distributed under the
  [SIL Open Font License, Version 1.1](cast2gif/fonts/SourceCodePro/OFL.txt)
