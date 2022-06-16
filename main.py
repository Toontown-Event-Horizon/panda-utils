#!/usr/bin/env python

import argparse
import os
from configparser import ConfigParser
from traceback import print_exc

from code import util
from code.shell import PandaShell
from code.tools import convert, palettize, downscale


def get_config() -> dict:
    cp = ConfigParser()
    path = os.path.dirname(os.path.abspath(__file__))
    cp.read(f'{path}/config.ini')
    return cp


def make_context() -> util.Context:
    return util.Context.from_config(get_config())


def loop(shell):
    try:
        shell.cmdloop()
    except Exception:  # noqa
        print_exc()
        loop(shell)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Perform various Panda3D model manipulations.')
    sp = parser.add_subparsers(description='Action to perform.', dest='action', required=True)

    # accepts no arguments
    shell_parser = sp.add_parser('shell')
    # accepts one argument - path to .bam file
    bam2egg_parser = sp.add_parser('bam2egg')
    bam2egg_parser.add_argument('input', help='The .bam file to convert')
    # accepts two arguments - directory to parse and target scale
    downscale_parser = sp.add_parser('downscale')
    downscale_parser.add_argument('path', help='The directory path to downscale')
    downscale_parser.add_argument('scale', help='The target scale', choices=[128, 256, 512, 1024, 2048], type=int)
    downscale_parser.add_argument('--force', help='True if the images with incorrect ratios should be resized',
                                  action='store_true')
    # accepts three or more arguments - model name, phase number, subdirectory in models
    palettize_parser = sp.add_parser('palettize')
    palettize_parser.add_argument('output', help='The name for the resulting .bam file')
    palettize_parser.add_argument('phase', default='3.5', help='The phase number to process')
    palettize_parser.add_argument('subdir', default='gui', help='The subdirectory inside models',
                                  choices=['char', 'gui', 'props', 'misc', 'fonts', 'shaders', 'modules'])
    palettize_parser.add_argument('--pattern', default='*',
                                  help='The image pattern to work with - defaults to all images in the directory.')

    ans = parser.parse_args()
    if ans.action == 'shell':
        psh = PandaShell.from_config(get_config())
        loop(psh)
    elif ans.action == 'bam2egg':
        convert.bam2egg(make_context(), ans.input)
    elif ans.action == 'palettize':
        palettize.palettize(make_context(), ans.output, ans.phase, ans.subdir, *ans.pattern.split())
    elif ans.action == 'downscale':
        downscale.downscale(make_context(), ans.path, ans.scale, force=ans.force)
