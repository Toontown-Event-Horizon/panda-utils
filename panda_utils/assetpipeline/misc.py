import logging
import os.path
import subprocess

logger = logging.getLogger("panda_utils.pipeline.misc")


def action_script(ctx, script_file):
    logger.info("%s: Running script %s", ctx.name, script_file)
    path = os.path.normpath(os.path.join(ctx.initial_wd, script_file))
    subprocess.run([path, ctx.model_name])
