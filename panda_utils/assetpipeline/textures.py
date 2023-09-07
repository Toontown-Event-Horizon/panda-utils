import logging

from panda_utils import util
from panda_utils.assetpipeline.commons import AssetContext
from panda_utils.tools.downscale import downscale

logger = logging.getLogger("panda_utils.pipeline.textures")


def action_downscale(ctx: AssetContext, size, bbox=-1, flags="", name=""):
    target_size = int(size)
    if target_size & (target_size - 1):
        raise ValueError("The target size must be a power of two!")

    bbox = int(bbox)
    flag_list = flags.split(",")
    force = bbox >= 0 or "truecenter" in flag_list or "force" in flag_list
    downscale(ctx.putil_ctx, ".", target_size, force, bbox, "truecenter" in flag_list, False, name, False)


def action_texture_cards(ctx: AssetContext, size=None):
    args = ["-o", f"{ctx.model_name}.egg"]
    if size:
        args += ["-p", f"{size},{size}"]
    args += [file for file in ctx.files if file.endswith(".png")]
    util.run_panda(ctx.putil_ctx, "egg-texture-cards", *args)
