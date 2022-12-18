#!/usr/bin/env python

import argparse
import os
from configparser import ConfigParser

from panda_utils import util
from panda_utils.tools import animconvert, convert, palettize, downscale, toontown


def get_config() -> dict:
    cp = ConfigParser()
    path = os.path.dirname(os.path.abspath(__file__))
    cp.read(f"{path}/config.ini")
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


def convert_dict(argument: str) -> dict[str, str]:
    arg_split = [x.split("=") for x in argument.split(",")]
    return {x[0]: x[1] for x in arg_split}


ArgumentDescriptions = {
    "input": Argument("input", "Input file"),
    "output": Argument("output", "Output file"),
    "phase": Argument("phase", "The phase number to process", default="3.5"),
    "subdir": Argument(
        "subdir",
        "The output subdirectory under models/",
        default="gui",
        choices=["char", "gui", "props", "misc", "fonts", "shaders", "modules"],
    ),
    "poly": Argument("--poly", "Set the size of a 1x1 node, in pixels.", "-p", type=int, default=0),
    "margin": Argument("--margin", "Set the margin between textures, in pixels.", "-m", type=int, default=0),
    "ordered": Argument(
        "--ordered",
        "True if the palette should be ordered. The names of the input files should start with <number>-..",
        "-O",
        action="store_true",
    ),
    "scale": Argument("scale", "The target scale.", choices=[32, 64, 128, 256, 512, 1024], type=int),
    "force": Argument("--force", "Resize images with wrong ratios.", "-f", action="store_true"),
    "bbox": Argument(
        "--bbox",
        "The preferred distance between the image boundary and the opaque areas, in %.",
        "-b",
        type=int,
        default=-1,
    ),
    "truecenter": Argument("--truecenter", "Use true center for wide squished images", "-c", action="store_true"),
    "triplicate": Argument("--triplicate", "Add LOD names to the files", "-T", action="store_true"),
    "reverse": Argument("--reverse", "Copy from the project folder to the working folder", "-r", action="store_true"),
    "ignore_current_scale": Argument(
        "--ignore-current-scale",
        "Resize images even if their target size equals the current size",
        "-I",
        action="store_true",
    ),
    "conversion_names": Argument(
        "conversion_names",
        "List of comma-separated joint pairs",
        type=convert_dict,
    )
}


ContextCommands = {
    "bam2egg": (convert.bam2egg, "input"),
    "egg2bam": (convert.egg2bam, "input", "triplicate"),
    "palettize": (palettize.palettize, "output", "phase", "subdir", "poly", "margin", "ordered"),
    "downscale": (downscale.downscale, "input", "scale", "force", "bbox", "truecenter", "ignore_current_scale"),
    "pipeline": (convert.patch_pipeline, "input"),
    "tbn": (convert.eggtrans, "input"),
    "copy": (convert.copy, "input", "reverse"),
    "abspath": (convert.patch_egg, "input"),
    "triplicate": (convert.build_lods, "input"),
    "toonhead": (toontown.toon_head, "input", "triplicate"),
    "animrename": (animconvert.animation_rename_bulk, "input", "output", "conversion_names"),
    "fromfile": (None, "input"),
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Perform various Panda3D model manipulations.")
    sp = parser.add_subparsers(description="Action to perform.", dest="action", required=True)

    for argname, (func, *args) in ContextCommands.items():
        subparser = sp.add_parser(argname)
        for arg in args:
            ArgumentDescriptions[arg](subparser)

    ans = parser.parse_args()
    ctx = make_context()

    if ans.action == "fromfile":
        with open(ans.input, "r") as f:
            arguments = f.read()

        ans = parser.parse_args(arguments.split(" "))

    if ans.action == "copy":
        if ans.reverse:
            convert.copy(ctx.resources_path, ctx.working_path, ans.input)
        else:
            convert.copy(ctx.working_path, ctx.resources_path, ans.input)
    elif ans.action in ContextCommands:
        command, *args = ContextCommands[ans.action]
        if command is None:
            print("Command not implemented")
            exit(1)
        command(ctx, **{("path" if arg == "input" else arg): getattr(ans, arg) for arg in args})
