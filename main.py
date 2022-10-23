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


class Argument:
    def __init__(self, name, description, other=None, **kwargs):
        self.name = name
        self.description = description
        self.other = other
        self.kwargs = kwargs

    def __call__(self, argparser):
        if self.other is not None:
            argparser.add_argument(self.name, self.other, help=self.description, **self.kwargs)
        else:
            argparser.add_argument(self.name, help=self.description, **self.kwargs)


ArgumentDescriptions = {
    "input": Argument("input", "Input file"),
    "output": Argument("output", "Output file"),
    "phase": Argument("phase", "The phase number to process", default="3.5"),
    "subdir": Argument(
        "subdir", "The output subdirectory under models/", default="gui",
        choices=['char', 'gui', 'props', 'misc', 'fonts', 'shaders', 'modules']
    ),
    "poly": Argument("--poly", "Set the size of a 1x1 node, in pixels.", "-p", type=int, default=0),
    "margin": Argument("--margin", "Set the margin between textures, in pixels.", "-m", type=int, default=0),
    "ordered": Argument(
        "--ordered",
        "True if the palette should be ordered. The names of the input files should start with <number>-..", "-O",
        action="store_true"
    ),
    "scale": Argument("scale", "The target scale.", choices=[32, 64, 128, 256, 512, 1024], type=int),
    "force": Argument("--force", "Resize images with wrong ratios.", "-f", action="store_true"),
    "bbox": Argument(
        "--bbox", "The preferred distance between the image boundary and the opaque areas, in %.", "-b",
        type=int, default=-1
    ),
    "truecenter": Argument("--truecenter", "Use true center for wide squished images", "-c", action="store_true"),
}


ContextCommands = {
    'bam2egg': (convert.bam2egg, "input"),
    'palettize': (palettize.palettize, "output", "phase", "subdir", "poly", "margin", "ordered"),
    'downscale': (downscale.downscale, "input", "scale", "force", "bbox", "truecenter"),
    'pipeline': (convert.patch_pipeline, "input"),
    'tbn': (convert.eggtrans, "input"),
    'abspath': (convert.patch_egg, "input"),
    'toonhead': (toontown.toon_head, "input")
}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Perform various Panda3D model manipulations.')
    sp = parser.add_subparsers(description='Action to perform.', dest='action', required=True)

    for argname, (func, *args) in ContextCommands.items():
        subparser = sp.add_parser(argname, help=func.__doc__)
        for arg in args:
            ArgumentDescriptions[arg](subparser)

    ans = parser.parse_args()
    ctx = make_context()

    if ans.action == 'copy':
        if ans.reverse:
            convert.copy(ctx.resources_path, ctx.working_path, ans.input)
        else:
            convert.copy(ctx.working_path, ctx.resources_path, ans.input)
    elif ans.action in ContextCommands:
        command, *args = ContextCommands[ans.action]
        command(ctx, **{("path" if arg == "input" else arg): getattr(ans, arg) for arg in args})

