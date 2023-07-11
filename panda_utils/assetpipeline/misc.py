import importlib
import logging

logger = logging.getLogger("panda_utils.pipeline.misc")


def action_script(ctx, script_file):
    logger.info("%s: Running script %s", ctx.name, script_file)
    mod = importlib.import_module(f"scripts.{script_file}")
    mod.run(ctx)
