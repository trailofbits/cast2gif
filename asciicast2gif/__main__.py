#!/usr/bin/env python3

import argparse
import os
import sys

from PIL import ImageFont

from . import AsciiCast
from .asciicast import VERSION_NAME


class StatusLogger(object):
    def __init__(self, width=30):
        self.last_percent = -1
        self.width = width

    def log_frame(self, frame, num_frames):
        percent_done = float(int(float(frame) / float(num_frames) * 1000.0)) / 10.0
        if percent_done > self.last_percent:
            self.clear()

            sys.stderr.write('[')
            bar_length = int((percent_done / 100.0) * (self.width-2) + 0.5)

            percent_string = "%.1f%%" % percent_done

            percent_start = int((self.width - 2 - len(percent_string)) / 2)

            for i in range(self.width - 2):
                if i == percent_start:
                    sys.stderr.write(percent_string)
                elif percent_start < i < percent_start + len(percent_string):
                    continue
                elif i < bar_length - 1 or percent_done >= 100:
                    sys.stderr.write('=')
                elif i == bar_length - 1:
                    sys.stderr.write('>')
                else:
                    sys.stderr.write('-')

            sys.stderr.write(']')
            sys.stderr.flush()
            self.last_percent = percent_done

    def clear(self):
        sys.stderr.write("\r%s\r" % ' ' * self.width)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Converts AsciiCast terminal recordings to animated GIFs')
    parser.add_argument('-v', '--version', action='store_true', default=False, help='Print version information and exit')
    parser.add_argument('ASCIICAST', type=str, help='The AsciiCast v2 file to convert, or \'-\' for STDIN')
    parser.add_argument('-o', '--output', type=str, default=None, help='The path for the output GIF file, or \'-\' for STDOUT (default is the input filename plus \'.gif\', or STDOUT if the input file is STDIN)')
    parser.add_argument('--force', action='store_true', default=False, help='Overwrite the output file even if it already exists')
    parser.add_argument('--font', type=str, default=None, help='Path to a TrueType font for rendering; defaults to SourceCodePro')
    parser.add_argument('-s', '--font-size', type=int, default=12, help='Font size (default=12)')
    parser.add_argument('--fps', type=int, default=None, help='Speficy the number of frames per second in the output GIF; by default, an optimal FPS is calculated')
    parser.add_argument('--idle-time-limit', type=float, default=None, help='The maximum amount of idle time that can occur between terminal events; by default this is read from the AsciiCast input, or set to zero if none is specified in the input; if provided, this option will override whatever is specified in the input')
    parser.add_argument('--loop', type=int, default=0, help='The number of times the GIF should loop, or zero if it should loop forever (default=0)')
    parser.add_argument('--quiet', action='store_true', default=False, help='Suppress all logging and status printouts')
    parser.add_argument('--width', type=int, default=None, help='Override the output width')
    parser.add_argument('--height', type=int, default=None, help='Override the output height')

    if argv is None:
        argv = sys.argv

    args = parser.parse_args(argv[1:])

    if args.version:
        print(VERSION_NAME)
        sys.exit(0)

    if args.font is None:
        args.font = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Source_Code_Pro', 'SourceCodePro-Regular.ttf')
        
    if args.ASCIICAST == '-':
        input_stream = sys.stdin
    else:
        input_stream = open(args.ASCIICAST, 'rb')
    try:
        input_isatty = input_stream.isatty()
        cast = AsciiCast(input_stream.read(), width=args.width, height=args.height)
    finally:
        if input_stream != sys.stdin:
            input_stream.close()
        
    if args.output is None:
        if input_isatty:
            args.output = '-'
        else:
            args.output = "%s.gif" % args.ASCIICAST
    if args.output == '-':
        output_stream = sys.stdin
    else:
        if not args.force and os.path.exists(args.output):
            if not args.quiet:
                sys.stderr.write("Error: output file %s already exists! Use --force to overwrite it.\n" % args.output)
            sys.exit(1)
        output_stream = open(args.output, 'wb')
    try:

        font = ImageFont.truetype(font=args.font, size=args.font_size)
        if args.quiet:
            status_logger = None
            frame_callback = None
        else:
            status_logger = StatusLogger()
            frame_callback = status_logger.log_frame
        cast.render(output_stream, font, fps=args.fps, idle_time_limit=args.idle_time_limit, loop=args.loop, frame_callback=frame_callback)

        if not output_stream.isatty() and not args.quiet:
            status_logger.clear()
            sys.stderr.write('Saved AsciiCast to %s\n' % output_stream.name)

    finally:
        if output_stream != sys.stdout:
            output_stream.close()


if __name__ == '__main__':
    main()
