import logging
import os
import pathlib
import shutil
import sys

from panda_utils import util
from panda_utils.assetpipeline import imports
from panda_utils.assetpipeline.commons import (
    AssetContext, BUILT_FOLDER, INTERMEDIATE_FOLDER, regex_mcf,
    regex_mcf_fallback,
)
from panda_utils.util import Context

OUTPUT_PARENT = "built"
# The pipeline will look for this file inside the input data whenever a [] callback is encountered
logger = logging.getLogger("panda_utils.pipeline")


def main(enable_logging=False):
    if enable_logging:
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter("%(name)-12s: %(levelname)-8s %(message)s")
        console.setFormatter(formatter)
        global_logger = logging.getLogger("")
        global_logger.setLevel(logging.INFO)
        global_logger.addHandler(console)

    _, input_folder, model_output, texture_output, *pipeline = sys.argv
    logger.info("Running Pipeline with parameters: %s", pipeline)
    input_folder = pathlib.Path(input_folder)
    ctx = AssetContext(input_folder, model_output, texture_output)

    intermediate_local = INTERMEDIATE_FOLDER / str(pathlib.PurePosixPath(ctx.built_model_path)).replace("/", "__")
    INTERMEDIATE_FOLDER.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(intermediate_local, ignore_errors=True)
    shutil.copytree(input_folder, intermediate_local)

    resources_path = BUILT_FOLDER.absolute()
    ctx.output_model.mkdir(parents=True, exist_ok=True)
    ctx.output_texture.mkdir(parents=True, exist_ok=True)
    os.chdir(intermediate_local)

    ctx.cwd = pathlib.Path(os.getcwd())
    ctx.putil_ctx = Context.from_config(
        {"options": {"panda3d_path_inherit": 1}, "paths": {"resources": resources_path}}
    )

    ctx.load_model_config()
    for method in pipeline:
        if not ctx.valid:
            logger.warning("The context for %s was aborted", ctx.name)
            return

        mcf, mcf_fallback = regex_mcf.match(method), regex_mcf_fallback.match(method)
        if mcf or mcf_fallback:
            use_fallback = mcf_fallback
            method_name = method[:-2]
            args = ()
            use_config = True
        else:
            method_name, *args = method.split(":")
            use_config = use_fallback = False
        action = imports.ALL_ACTIONS.get(method_name)
        if not action:
            logger.error("Action %s not found", method_name)
            # exit(1)
        else:
            if use_config:
                ctx.run_action_through_config(action, method_name, use_fallback)
            else:
                action(ctx, *args)


if __name__ == "__main__":
    main(util.get_debug(util.LoggingScope.PIPELINE))
