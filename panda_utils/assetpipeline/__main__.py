import logging
import os
import shutil
import sys

from panda_utils.assetpipeline import imports
from panda_utils.util import Context

OUTPUT_PARENT = "built"


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

    @property
    def files(self):
        return os.listdir()


def main():
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter("%(name)-12s: %(levelname)-8s %(message)s")
    console.setFormatter(formatter)
    logger = logging.getLogger("")
    logger.setLevel(logging.INFO)
    logger.addHandler(console)

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
        method_name, *args = method.split(":")
        action = imports.ALL_ACTIONS.get(method_name)
        if not action:
            logger.error("Action %s not found", method_name)
            # exit(1)
        else:
            action(ctx, *args)


if __name__ == "__main__":
    main()
