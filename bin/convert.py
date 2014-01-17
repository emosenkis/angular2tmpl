#!/usr/bin/env python2.7

from __future__ import (division, absolute_import, print_function,
                        unicode_literals)

import argparse
import importlib
import logging
import sys

from angular2tmpl import core


LOGGER = logging.getLogger(__name__)
LOG_LEVELS = [
    logging.WARNING,
    logging.INFO,
    logging.DEBUG,
]


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('--infile',
                        type=argparse.FileType('r'),
                        default=sys.stdin,
                        help='defaults to stdin')
    parser.add_argument('--outfile',
                        type=argparse.FileType('w'),
                        default=sys.stdout,
                        help='defaults to stdout')
    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help='can be repeated')
    parser.add_argument('--module', action='append', default=[],
                        help='Python path of a Module to load;'
                        ' can be repeated')
    parser.add_argument('--ng', type=bool, default=True,
                        help='use --ng=false to skip loading the ng Module')
    args = parser.parse_args(args)
    logging.basicConfig(level=LOG_LEVELS[min(args.verbose,
                                             len(LOG_LEVELS) - 1)])
    LOGGER.info('Converting %s => %s',
                args.infile.name, args.outfile.name)
    converter = core.Converter(loadNg=args.ng)
    for module in args.module:
        parts = module.split('.')
        pymodule = '.'.join(parts[:-1])
        name = parts[-1]
        LOGGER.info('Loading module %s from %s', name, pymodule)
        converter.module(getattr(importlib.import_module(pymodule), name))
    args.outfile.write(converter.Convert(args.infile))


if __name__ == '__main__':
    main(sys.argv[1:])
