import importlib
import logging
import os
import shutil

from panda_utils.assetpipeline.commons import AssetContext

logger = logging.getLogger("panda_utils.pipeline.misc")


def action_script(ctx: AssetContext, script_file, *arguments):
    logger.info("%s: Running script %s", ctx.name, script_file)
    mod = importlib.import_module(f"scripts.{script_file}")

    if script_file[-2:] in ("[]", "{}"):
        ctx.run_action_through_config(mod.run, f"script/{script_file}", script_file[-2:] == "{}")
    else:
        ctx.run_action(mod.run, arguments, convert_list=True)


def action_cts(ctx: AssetContext, injection_name):
    inject_path = ctx.get_injection_path(injection_name)
    if inject_path is None:
        logger.warning("%s: Unable to find common texture set: %s", ctx.name, injection_name)
        return

    for file_name in os.listdir(inject_path):
        ctx.copy_ignores.add(file_name)
        shutil.copy(inject_path / file_name, file_name)
    logger.info("%s: Copied common texture set %s", ctx.name, injection_name)


def action_uncache(ctx: AssetContext):
    ctx.uncache_eggs()
