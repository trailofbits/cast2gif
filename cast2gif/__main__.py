#!/usr/bin/env python3

import argparse
import os
from pathlib import Path
import sys
from typing import Optional

from . import __version_name__
from .asciicast import AsciiCast
from .fonts import FontCollection
from .recording import TerminalRecording


class StatusLogger:
    def __init__(self, width: Optional[int] = None):
        self.last_percent: int = -1
        if width is None:
            width = max(os.get_terminal_size().columns, 30)
        self.width: int = width

    def log_frame(self, frame: int, num_frames: int):
        percent_done = float(int(float(frame) / float(num_frames) * 1000.0)) / 10.0
        if percent_done > self.last_percent:
            self.clear()

            sys.stderr.write("[")
            bar_length = int((percent_done / 100.0) * (self.width - 2) + 0.5)

            percent_string = f"{percent_done:.1f}%"

            percent_start = int((self.width - 2 - len(percent_string)) / 2)

            for i in range(self.width - 2):
                if i == percent_start:
                    sys.stderr.write(percent_string)
                elif percent_start < i < percent_start + len(percent_string):
                    continue
                elif i < bar_length - 1 or percent_done >= 100:
                    sys.stderr.write("=")
                elif i == bar_length - 1:
                    sys.stderr.write(">")
                else:
                    sys.stderr.write("-")

            sys.stderr.write("]")
            sys.stderr.flush()
            self.last_percent = percent_done

    def clear(self):
        sys.stderr.write(f"\r{' ' * self.width}\r")
        sys.stderr.flush()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Converts AsciiCast terminal recordings to animated GIFs"
    )
    parser.add_argument(
        "-v",
        "--version",
        action="store_true",
        default=False,
        help="Print version information and exit",
    )
    parser.add_argument(
        "ASCIICAST", type=str, nargs="?", default=None,
        help="The AsciiCast v2 file to convert, or '-' for STDIN (the default)"
    )
    parser.add_argument(
        "--exec", "-c", nargs=argparse.REMAINDER, help="Instead of parsing an AsciiCast v2 file, run the command "
                                                       "immediately after `--exec` and use its output"
    )
    parser.add_argument(
        "--hide-prompt", action="store_true", help="By default, when using the `--exec` argument to run a command, "
                                                   "the command prompt is included before the command output; this "
                                                   "argument hides the prompt and only includes the output"
    )
    parser.add_argument(
        "--ps1", type=str, default=None,
        help="The PS1 command prompt to use in conjuction with the `--exec` output (default=\"${PS1}\", if it is set, "
             "otherwise \"$ \" in green)"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="The path for the output GIF file, or '-' for STDOUT (default is the input filename plus '.gif', or "
             "STDOUT if the input file is STDIN)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Overwrite the output file even if it already exists",
    )
    parser.add_argument(
        "--screenshot",
        "-sc",
        action="store_true",
        help="Render a screenshot rather than an animated gif"
    )
    parser.add_argument(
        "--font",
        type=str,
        action="append",
        help="Path to a TrueType font for rendering; defaults to SourceCodePro; this argument can be supplied multiple "
             "times, with additional fonts used in the event that one is missing a required glyph",
    )
    parser.add_argument(
        "-s", "--font-size", type=int, default=12, help="Font size (default=12)"
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=None,
        help="Speficy the number of frames per second in the output GIF; by default, an optimal FPS is calculated",
    )
    parser.add_argument(
        "--idle-time-limit",
        type=float,
        default=None,
        help="The maximum amount of idle time that can occur between terminal events; by default this is read from the "
             "AsciiCast input, or set to zero if none is specified in the input; if provided, this option will "
             "override whatever is specified in the input",
    )
    parser.add_argument(
        "--loop",
        type=int,
        default=0,
        help="The number of times the GIF should loop, or zero if it should loop forever (default=0)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress all logging and status printouts",
    )
    parser.add_argument(
        "--width", type=int, default=None, help="Override the output width"
    )
    parser.add_argument(
        "--height", type=int, default=None, help="Override the output height"
    )

    if argv is None:
        argv = sys.argv

    args = parser.parse_args(argv[1:])

    if args.version:
        print(__version_name__)
        sys.exit(0)

    if args.ASCIICAST is None and not args.exec:
        parser.print_usage(sys.stderr)
        sys.stderr.write("\nerror: you must provide either an AsciiCast v2 input file or use the `--exec` argument\n")
        sys.exit(1)
    elif args.ASCIICAST is not None and args.exec:
        parser.print_usage(sys.stderr)
        sys.stderr.write("\nerror: you may not provide both an AsciiCast v2 input file or use the `--exec` argument at "
                         "the same time\n")
        sys.exit(1)
    elif args.exec:
        input_isatty = False
        if args.hide_prompt:
            ps1: Optional[str] = None
        elif args.ps1 is not None:
            ps1 = args.ps1
        else:
            ps1 = os.getenv("PS1", "\u001b[32m$\u001b[0m ")
        recording: TerminalRecording = TerminalRecording.record(args.exec, ps1=ps1)
        if recording.return_value != 0 and sys.stderr.isatty() and not args.quiet:
            sys.stderr.write(f"\n\nWarning: `{' '.join(args.exec)}` exited with code {recording.return_value}\n\n")
    else:
        if args.ASCIICAST == "-":
            input_stream = sys.stdin
        else:
            input_stream = open(args.ASCIICAST, "rb")
        try:
            input_isatty = input_stream.isatty()
            recording = AsciiCast.load(input_stream.read(), width=args.width, height=args.height)
        finally:
            if input_stream != sys.stdin:
                input_stream.close()

    if args.output is None:
        if input_isatty:
            args.output = "-"
        else:
            args.output = "%s.gif" % args.ASCIICAST
    if args.output == "-":
        output_stream = sys.stdout
    else:
        if not args.force and os.path.exists(args.output):
            if not args.quiet:
                sys.stderr.write(
                    "Error: output file %s already exists! Use --force to overwrite it.\n"
                    % args.output
                )
            sys.exit(1)
        output_stream = open(args.output, "wb")
    try:
        if not args.font:
            font_dir = Path(__file__).absolute().parent / "fonts"
            font = FontCollection(
                font_dir / "FiraCode" / "Fira Code Regular Nerd Font Complete Mono.otf",
                font_dir / "Hack" / "Hack Regular Nerd Font Complete Mono.ttf",
                font_dir / "SourceCodePro" / "SourceCodePro-Regular.ttf",
                size=args.font_size
            )
        else:
            font = FontCollection(*args.font, size=args.font_size)

        if args.quiet or not sys.stderr.isatty():
            status_logger = None
            frame_callback = lambda *_: None
        else:
            status_logger = StatusLogger()
            frame_callback = status_logger.log_frame

        if args.screenshot:
            recording.screenshot(output_stream, font, frame_callback)
        else:
            recording.render(
                output_stream,
                font,
                fps=args.fps,
                idle_time_limit=args.idle_time_limit,
                loop=args.loop,
                frame_callback=frame_callback
            )

        if not output_stream.isatty() and not args.quiet and sys.stderr.isatty():
            if status_logger is not None:
                status_logger.clear()
            sys.stderr.write("Saved AsciiCast to %s\n" % output_stream.name)

    finally:
        if output_stream != sys.stdout:
            output_stream.close()


if __name__ == "__main__":
    main()
