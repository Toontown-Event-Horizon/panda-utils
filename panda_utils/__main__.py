#!/usr/bin/env python

import argparse
import logging

from panda_utils import util
from panda_utils.tools import animconvert, convert, palettize, downscale, toontown


def get_config() -> dict:
    from configparser import ConfigParser
    import platformdirs

    cp = ConfigParser()
    path = platformdirs.user_config_path("panda-utils")
    success_reading = cp.read(path)
    if not success_reading:
        print(f"The configuration file not found! Copy config_example.ini into {path} and edit it as needed.")
        exit(1)
    return {s: dict(cp.items(s)) for s in cp.sections()}


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
    ),
}


ContextCommands = {
    "bam2egg": ("Converts Bam files to Egg files, copying missing resources.", convert.bam2egg, "input"),
    "egg2bam": ("Converts Egg files to Bam files, copying missing resources.", convert.egg2bam, "input", "triplicate"),
    "palettize": (
        "Creates palettes of 2D images.",
        palettize.palettize,
        "output",
        "phase",
        "subdir",
        "poly",
        "margin",
        "ordered",
    ),
    "downscale": (
        "Rescales a set of 2D images to the given size.",
        downscale.downscale,
        "input",
        "scale",
        "force",
        "bbox",
        "truecenter",
        "ignore_current_scale",
    ),
    "pipeline": ("Fixes binormals and resource paths on a Bam file.", convert.patch_pipeline, "input"),
    "tbn": ("Fixes binormals on a Egg file.", convert.eggtrans, "input"),
    "copy": (
        "Copies a file from the working directory into the dist directory, or vice versa.",
        convert.copy,
        "input",
        "reverse",
    ),
    "abspath": ("Fixes absolute paths on a Egg file.", convert.patch_egg, "input"),
    "triplicate": (
        "Copies a file for 1000, 500, and 250 LOD. Does not decimate the model.",
        convert.build_lods,
        "input",
    ),
    "toonhead": ("Fixes toon head models for Toontown purposes.", toontown.toon_head, "input", "triplicate"),
    "animrename": (
        "Changes joint names on an animation.",
        animconvert.animation_rename_bulk,
        "input",
        "output",
        "conversion_names",
    ),
    "fromfile": ("Run a command written inside a text file.", None, "input"),
}


def main():
    util.interactive = True

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter("%(name)-12s: %(levelname)-8s %(message)s")
    console.setFormatter(formatter)
    logger = logging.getLogger("panda_utils")
    logger.setLevel(logging.INFO)
    logger.addHandler(console)

    parser = argparse.ArgumentParser(prog="panda_utils", description="Perform various Panda3D model manipulations.")
    sp = parser.add_subparsers(description="Action to perform.", dest="action", required=True)

    for argname, (desc, func, *args) in ContextCommands.items():
        subparser = sp.add_parser(argname, help=desc)
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
        description, command, *args = ContextCommands[ans.action]
        if command is None:
            print("Command not implemented")
            exit(1)
        command(ctx, **{("path" if arg == "input" else arg): getattr(ans, arg) for arg in args})


if __name__ == "__main__":
    main()
