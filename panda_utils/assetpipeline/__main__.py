import logging
import os
import pathlib
import shutil
import sys

import yaml

from panda_utils.assetpipeline import imports
from panda_utils.eggtree import eggparse
from panda_utils.util import Context

OUTPUT_PARENT = "built"
# The pipeline will look for this file inside the input data whenever a [] callback is encountered
YAML_CONFIG_FILENAME = "model-config.yml"
logger = logging.getLogger("panda_utils.pipeline")


class AssetContext:
    def __init__(self, input_folder, output_phase, output_folder):
        self.input_folder = input_folder
        self.output_phase = output_phase
        self.output_folder = output_folder
        self.valid = True

        self.initial_wd = os.getcwd()
        self.model_name = input_folder.split("/")[-1]
        self.name = self.model_name.replace("-", " ").replace("_", " ").title()

        self.intermediate_path = f"{OUTPUT_PARENT}/{output_phase}/models/{output_folder}/{self.model_name}"
        self.output_model_rel = f"{output_phase}/models/{output_folder}"
        self.output_model = os.path.abspath(os.path.dirname(self.intermediate_path))
        self.output_texture = os.path.abspath(f"{OUTPUT_PARENT}/{output_phase}/maps")
        self.eggs = None
        self.path_overrides = {}
        self.post_remove = set()

    def cache_eggs(self):
        if self.eggs is not None:
            return

        self.eggs = {}
        for file in self.files:
            if file.endswith(".egg"):
                with open(file) as f:
                    tree = eggparse.egg_tokenize(f.readlines())
                self.eggs[file] = tree

    def uncache_eggs(self):
        if self.eggs is None:
            return

        for file, tree in self.eggs.items():
            with open(file, "w") as f:
                f.write(str(tree))
        self.eggs = None

    @property
    def files(self):
        return sorted(os.listdir())

    @staticmethod
    def get_injection_path(name):
        injections_base_path = pathlib.Path("..", "..", "common")
        all_injections = os.listdir(injections_base_path)
        if name not in all_injections:
            return None
        return injections_base_path / name

    def run_action_through_config(self, action, name):
        if YAML_CONFIG_FILENAME not in self.files:
            return

        with open(YAML_CONFIG_FILENAME) as f:
            data = yaml.safe_load(f)

        if name not in data:
            return

        args = data[name]
        if isinstance(args, list):
            for kwargs in args:
                self.run_action(action, kwargs)
        else:
            self.run_action(action, args)

    def run_action(self, action, args):
        if isinstance(args, dict):
            action(self, **args)
        elif isinstance(args, str):
            action(self, args)
        else:
            logger.warning("%s: Invalid configured arguments: %s (expected dict, or str)", self.name, type(args))

    @staticmethod
    def reverse_rmdir(path):
        while not os.listdir(path):
            path.rmdir()
            path = path.parent
            if path[-1] == OUTPUT_PARENT:
                break


def main(enable_logging=False):
    if enable_logging:
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter("%(name)-12s: %(levelname)-8s %(message)s")
        console.setFormatter(formatter)
        global_logger = logging.getLogger("")
        global_logger.setLevel(logging.INFO)
        global_logger.addHandler(console)

    _, input_folder, output_phase, output_folder, *pipeline = sys.argv
    ctx = AssetContext(input_folder, output_phase, output_folder)

    intermediate_folder = "intermediate/" + ctx.intermediate_path.replace("/", "__")
    os.makedirs("intermediate", exist_ok=True)
    if os.path.exists(intermediate_folder):
        shutil.rmtree(intermediate_folder)
    shutil.copytree(input_folder, intermediate_folder)

    resources_path = os.path.abspath(OUTPUT_PARENT)
    os.makedirs(ctx.output_model, exist_ok=True)
    os.makedirs(ctx.output_texture, exist_ok=True)
    os.chdir(intermediate_folder)

    ctx.cwd = os.getcwd()
    ctx.putil_ctx = Context.from_config(
        {"options": {"panda3d_path_inherit": 1}, "paths": {"resources": resources_path}}
    )

    for method in pipeline:
        if not ctx.valid:
            logger.warning("The context for %s was aborted", ctx.name)
            return

        if method.endswith("[]"):
            method_name = method[:-2]
            args = ()
            use_config = True
        else:
            method_name, *args = method.split(":")
            use_config = False
        action = imports.ALL_ACTIONS.get(method_name)
        if not action:
            logger.error("Action %s not found", method_name)
            # exit(1)
        else:
            if use_config:
                ctx.run_action_through_config(action, method_name)
            else:
                action(ctx, *args)


if __name__ == "__main__":
    main(bool(os.getenv("PANDA_UTILS_LOGGING")))
