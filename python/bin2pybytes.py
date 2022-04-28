#!/usr/bin/env python

import argparse
import sys


def yield_chunks(fp, chunksize):
    while True:
        rv = fp.read(chunksize if chunksize else -1)
        if not rv:
            return None
        yield rv


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', default=False, action='store_true',
            help='Format output as bytes instead of string.')
    parser.add_argument('-v', default='buf', help='Name of variable')
    parser.add_argument('-l', default=80, type=int, help='maximum line length')
    parser.add_argument(
            'infile', default=sys.stdin.buffer, type=argparse.FileType('rb'),
            nargs='?', help='File to convert to var')
    parser.add_argument(
            'outfile', default=sys.stdout, type=argparse.FileType('w'),
            nargs='?', help='File to convert to var')
    args = parser.parse_args(argv[1:])

    min_line = len("{} += {}\"\"".format(args.v, 'b' if args.b else ''))
    if args.l <= min_line:
        chunksize = 0
    else:
        chunksize = (args.l - min_line)//4  # 4 output chars per byte
    print("{}  = {}\"\"".format(args.v, 'b' if args.b else ''),
            file=args.outfile)
    for chunk in yield_chunks(args.infile, chunksize):
        data = "".join("\\x{:02x}".format(b) for b in chunk)
        print("{} += {}\"{}\"".format(args.v, 'b' if args.b else '', data),
                file=args.outfile)


if __name__ == '__main__':
    main(sys.argv)
