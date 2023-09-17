import logging
import os
import pathlib
import re

import yaml

from panda_utils.eggtree import eggparse
from panda_utils.util import Context

INPUT_FOLDER = pathlib.Path("input")
INTERMEDIATE_FOLDER = pathlib.Path("intermediate")
BUILT_FOLDER = pathlib.Path("built")
YAML_CONFIG_FILENAME = "model-config.yml"
logger = logging.getLogger("panda_utils.pipeline")
preblend_regex = re.compile(r".*\.(fbx|obj)")
regex_mcf = re.compile(r".*\[]$")
regex_mcf_fallback = re.compile(r".*\{}$")
command_regex = re.compile("^[a-zA-Z_0-9-]+$")
file_out_regex = re.compile(r".*((-[0-9]+)?|_palette_.+)\.(png|jpg|rgb)$")


class AssetContext:
    cwd: pathlib.Path
    putil_ctx: Context

    def __init__(self, input_folder, model_output, texture_output):
        self.input_folder = input_folder
        self.model_name = input_folder.name
        self.output_model_rel = pathlib.Path(pathlib.PurePosixPath(model_output.replace("\\", "/")))
        self.output_texture_rel = pathlib.Path(pathlib.PurePosixPath(texture_output.replace("\\", "/")))
        self.output_model = pathlib.Path(BUILT_FOLDER, self.output_model_rel).absolute()
        self.output_texture = pathlib.Path(BUILT_FOLDER, self.output_texture_rel).absolute()
        self.built_model_path = pathlib.Path(self.output_model_rel, self.model_name)

        self.output_texture_egg = str(pathlib.PurePosixPath(texture_output))
        try:
            other_option = str(pathlib.PurePosixPath(self.output_texture.relative_to(self.output_model)))
        except ValueError:
            pass
        else:
            self.output_texture_egg = other_option
        if self.output_texture_egg.startswith("/") or "\\" in self.output_texture_egg:
            raise ValueError(f"Unexpected absolute path for the texture output: {self.output_texture_egg}!")

        self.valid = True

        self.initial_wd = os.getcwd()
        self.name = self.model_name.replace("-", " ").replace("_", " ").title()
        self.eggs = None
        self.copy_ignores = set()
        self.model_config = {}

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

    def load_model_config(self):
        if YAML_CONFIG_FILENAME not in self.files:
            data = {}
        else:
            with open(YAML_CONFIG_FILENAME) as f:
                data = yaml.safe_load(f)

        self.model_config = data

    def run_action_through_config(self, action, name, use_fallback):
        if name not in self.model_config:
            if use_fallback:
                self.run_action(action, {})
            return

        args = self.model_config[name]
        if isinstance(args, list):
            for kwargs in args:
                self.run_action(action, kwargs)
        else:
            self.run_action(action, args)

    def run_action(self, action, args, convert_list=False):
        if isinstance(args, dict):
            action(self, **args)
        elif isinstance(args, str):
            action(self, args)
        elif convert_list and (isinstance(args, list) or isinstance(args, tuple)):
            action(self, *args)
        else:
            logger.warning("%s: Invalid configured arguments: %s (expected dict, or str)", self.name, type(args))
