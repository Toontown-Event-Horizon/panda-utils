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
    downscale_parser.add_argument('scale', help='The target scale', choices=[64, 128, 256, 512, 1024], type=int)
    downscale_parser.add_argument('-f', '--force', help='True if the images with incorrect ratios should be resized',
                                  action='store_true')
    downscale_parser.add_argument('-b', '--bbox', help='Set the preferred distance between the image boundary and '
                                                       'the non-transparent area, in %', type=int, default=-1)
    downscale_parser.add_argument('-c', '--truecenter', help='Use true center for wide images with low height',
                                  action='store_true')
    # accepts three or more arguments - model name, phase number, subdirectory in models
    palettize_parser = sp.add_parser('palettize')
    palettize_parser.add_argument('output', help='The name for the resulting .bam file')
    palettize_parser.add_argument('phase', default='3.5', help='The phase number to process')
    palettize_parser.add_argument('subdir', default='gui', help='The subdirectory inside models',
                                  choices=['char', 'gui', 'props', 'misc', 'fonts', 'shaders', 'modules'])
    palettize_parser.add_argument('-p', '--poly', help='Set the size of a 1x1 node, in pixels.', type=int, default=0)

    ans = parser.parse_args()
    if ans.action == 'shell':
        psh = PandaShell.from_config(get_config())
        loop(psh)
    elif ans.action == 'bam2egg':
        convert.bam2egg(make_context(), ans.input)
    elif ans.action == 'palettize':
        palettize.palettize(make_context(), ans.output, ans.phase, ans.subdir, poly=ans.poly)
    elif ans.action == 'downscale':
        downscale.downscale(make_context(), ans.path, ans.scale, force=ans.force, bbox_crop=ans.bbox,
                            force_true_center=ans.truecenter)
