import logging
import pathlib
import shutil
import subprocess

from panda_utils import util
from panda_utils.assetpipeline.commons import AssetContext, preblend_regex
from panda_utils.util import get_data_file_path

logger = logging.getLogger("panda_utils.converter.blender")


def run_blender_raw(cwd, file, script, *args):
    args = [util.choose_binary("blender"), "--background", "--python", script, "--", *args]
    if file is not None:
        args.insert(1, file)
    stdout_pipe = subprocess.DEVNULL if not util.get_debug(util.LoggingScope.BLENDER) else None
    subprocess.run(args, stdout=stdout_pipe, cwd=cwd)


def run_blender(cwd, file, script, *args):
    run_blender_raw(cwd, file, get_data_file_path(script), *args)


def action_bscript(ctx: AssetContext, script):
    for file in ctx.files:
        if file.endswith(".blend"):
            logger.info("%s: Running bscript on file: %s", ctx.name, file)
            run_blender_raw(ctx.cwd, file, ctx.cwd.parent.parent / "bscripts" / script)


def action_preblend(ctx: AssetContext):
    all_inputs = [file for file in ctx.files if preblend_regex.match(file)]
    logger.info("%s: Converting to blend: %s", ctx.name, ", ".join(all_inputs))

    blend_filename = f"{ctx.model_name}.blend"
    run_blender(ctx.cwd, None, "blender/import_model.py", pathlib.Path.cwd() / blend_filename, *all_inputs)


def action_blendrename(ctx: AssetContext):
    count = 0
    for file in ctx.files:
        if file.endswith(".blend"):
            blend_filename = ctx.model_name
            if count:
                blend_filename += f"-{count}"
            blend_filename += ".blend"
            count += 1
            shutil.move(file, blend_filename)


def __make_blend2bam_args(binary, flags):
    args = []
    if "srgb" not in flags:
        args.append("--no-srgb")
    if "bullet" in flags:
        args.append("--collision-shapes" if binary == "gltf2bam" else "--physics-engine")
        args.append("bullet")
    if "legacy" in flags:
        if binary == "gltf2bam":
            args.append("--legacy-materials")
        else:
            args.append("--material-mode")
            args.append("legacy")
    return args


def __run_export_util(ctx: AssetContext, binary, input_file, output_file, flags):
    res = subprocess.run(
        [binary, *__make_blend2bam_args(binary, flags), input_file, output_file],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        cwd=ctx.cwd,
    )
    err = res.stderr.decode("utf-8")
    if err and "KeyError: 'nodes'" in err:
        logger.error("%s: Blender output an empty model, aborting.", ctx.name)
        ctx.valid = False
    elif err:
        logger.error("%s: Blender failed", ctx.name)
        print(err)
        exit(1)


def __run_blend2bam(ctx: AssetContext, file, flags):
    logger.info("%s: Patching texture paths: %s", ctx.name, file)
    full_path = pathlib.Path(ctx.cwd, file)
    run_blender(ctx.cwd, full_path, "blender/patch_paths.py")

    logger.info("%s: Converting to bam: %s", ctx.name, file)
    bam_filename = file[:-5] + "bam"
    __run_export_util(ctx, "blend2bam", file, bam_filename, flags)


def __run_gltf2bam(ctx: AssetContext, file, flags):
    logger.info("%s: Exporting to GLTF: %s", ctx.name, file)
    full_path = pathlib.Path(ctx.cwd, file)
    intermediate_file = file[:-5] + "glb"
    bam_filename = file[:-5] + "bam"
    target_path = pathlib.Path(ctx.cwd, intermediate_file)
    run_blender(ctx.cwd, full_path, "blender/export_glb.py", target_path)

    logger.info("%s: Converting to bam: %s", ctx.name, intermediate_file)
    __run_export_util(ctx, "gltf2bam", intermediate_file, bam_filename, flags)


def action_blend2bam(ctx: AssetContext, flags=""):
    flags = flags.lower().split(",")
    for file in ctx.files:
        if file.endswith(".blend"):
            if "b2b" in flags:
                __run_blend2bam(ctx, file, flags)
            else:
                __run_gltf2bam(ctx, file, flags)


def action_yabee(ctx: AssetContext, **kwargs):
    args_converted = [f"{target_name}::{blender_name}" for target_name, blender_name in kwargs.items()]
    for file in ctx.files:
        if file.endswith(".blend"):
            logger.info("%s: Exporting through YABEE: %s", ctx.name, file)
            full_path = pathlib.Path(ctx.cwd, file)
            egg_name = file[:-6] + ".egg"
            run_blender(ctx.cwd, full_path, "blender/patch_paths.py")
            run_blender(ctx.cwd, full_path, "blender/export_with_yabee.py", egg_name, *args_converted)

            target_name = ctx.model_name + ".egg"
            if egg_name != target_name:
                shutil.move(egg_name, target_name)
