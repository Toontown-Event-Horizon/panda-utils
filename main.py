#!/usr/bin/env python

import argparse
import os
from configparser import ConfigParser

from code import util
from code.tools import convert, palettize, downscale, toontown


def get_config() -> dict:
    cp = ConfigParser()
    path = os.path.dirname(os.path.abspath(__file__))
    cp.read(f'{path}/config.ini')
    return cp


def make_context() -> util.Context:
    return util.Context.from_config(get_config())


ContextCommands = {
    'bam2egg': (convert.bam2egg, "input"),
    'palettize': (palettize.palettize, "output", "phase", "subdir", "poly", "margin", "ordered"),
    'downscale': (downscale.downscale, "path", "scale", "force", "bbox", "truecenter"),
    'pipeline': (convert.patch_pipeline, "input"),
    'tbn': (convert.eggtrans, "input"),
    'abspath': (convert.patch_egg, "input"),
    'toonhead': (toontown.toon_head, "input")
}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Perform various Panda3D model manipulations.')
    sp = parser.add_subparsers(description='Action to perform.', dest='action', required=True)

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
    palettize_parser.add_argument('-m', '--margin', help='Set the margin between textures, in pixels.',
                                  type=int, default=0)
    palettize_parser.add_argument('-O', '--ordered',
                                  help='True if the palette should be ordered. The names of the input files '
                                       'should start with <number>-.',
                                  action='store_true')

    # accepts one argument - path to the file
    copy_parser = sp.add_parser('copy')
    copy_parser.add_argument('input', help='The path to the file to copy')
    copy_parser.add_argument('-r', '--reverse', help='Copy from resources instead', action='store_true')

    pipeline_parser = sp.add_parser('pipeline')
    pipeline_parser.add_argument('input', help='The input file to fix')

    tbn_parser = sp.add_parser('tbn')
    tbn_parser.add_argument('input', help='The input file to fix')

    abspath_parser = sp.add_parser('abspath')
    abspath_parser.add_argument('input', help='The input file to fix')

    toonhead_parser = sp.add_parser('toonhead')
    toonhead_parser.add_argument('input', help='The input file to fix')

    ans = parser.parse_args()
    ctx = make_context()

    if ans.action == 'copy':
        if ans.reverse:
            convert.copy(ctx.resources_path, ctx.working_path, ans.input)
        else:
            convert.copy(ctx.working_path, ctx.resources_path, ans.input)
    elif ans.action in ContextCommands:
        command, *args = ContextCommands[ans.action]
        command(ctx, *[getattr(ans, arg) for arg in args])

