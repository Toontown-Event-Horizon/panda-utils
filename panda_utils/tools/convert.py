import os
import pathlib
import shutil
import logging
from typing import List

from panda_utils import util

LODs = ["-1000", "-500", "-250"]

logger = logging.getLogger("panda_utils.converter")


def copy_single(source_path: pathlib.Path, target_path: pathlib.Path) -> None:
    if not source_path.exists():
        return

    if target_path.exists() and target_path.stat().st_mtime > source_path.stat().st_mtime:
        return

    target_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.is_dir():
        shutil.copytree(source_path, target_path, dirs_exist_ok=True)
    else:
        shutil.copy(source_path, target_path)


def copy(source: str, target: str, path: str, target_fn: str = None) -> None:
    if target_fn is None:
        target_fn = path
    source_path = pathlib.Path(source, path)
    target_path = pathlib.Path(target, target_fn)
    copy_single(source_path, target_path)

    for lod in LODs:
        if lod not in path:
            continue

        for other_lod in LODs:
            if other_lod == lod:
                continue

            new_source = str(source_path).replace(lod, other_lod)
            new_target = str(target_path).replace(lod, other_lod)
            copy_single(pathlib.Path(new_source), pathlib.Path(new_target))


def patch_egg(ctx: util.Context, path: str) -> None:
    with open(f"{ctx.working_path}/{path}") as f:
        data = f.read()

    if ctx.working_path not in data:
        return

    data = data.replace(f"{ctx.working_path}/", "").replace(ctx.working_path, "")
    with open(f"{ctx.working_path}/{path}", "w") as f:
        f.write(data)
    logger.info("Patched absolute source paths!")


def patch_pipeline(ctx: util.Context, path: str) -> None:
    oppath = f"{path}-operated"
    copy(ctx.working_path, ctx.working_path, path, oppath)
    for i in range(2):  # sometimes issues happen when running one time
        bam2egg(ctx, oppath)
        eggpath = oppath.replace(".bam", ".egg")
        eggtrans(ctx, eggpath)
        egg2bam(ctx, eggpath)
    copy(ctx.working_path, ctx.resources_path, oppath, path)


def eggtrans(ctx: util.Context, path: str) -> None:
    util.run_panda(ctx, "egg-trans", "-tbnall", path, "-o", path)


def copy_errors(ctx: util.Context, path: str, errored_files: List[str]) -> bool:
    partial_abspath = pathlib.Path(ctx.resources_path, *path.replace("\\", "/").split("/")[:-1])
    for x in errored_files:
        target_path = partial_abspath / x
        possible_paths = []
        if os.path.exists(rpx := pathlib.Path(ctx.resources_path, x)):
            possible_paths.append(rpx)
        if os.path.exists(abp := partial_abspath / x):
            possible_paths.append(abp)

        if not possible_paths:
            if util.interactive:
                p2 = input(f"Unable to find {x} in resources. Enter path to copy from: ")
            else:
                p2 = None
            if not p2:
                logger.error("Unable to get %s from anywhere, aborting.", x)
                return False
            possible_paths.append(p2)

        newest_file = max(possible_paths, key=os.path.getctime)
        if newest_file != target_path:
            logger.info("Copying %s from resources.", x)
            pathlib.Path(target_path).parent.mkdir(exist_ok=True, parents=True)
            shutil.copy(newest_file, target_path)

    return True


def egg2bam(ctx: util.Context, path: str, triplicate: bool = False, flags=()) -> None:
    command = ["egg2bam", path, "-o", path.replace(".egg", ".bam")]
    if "compress" in flags:
        command.append("-ctex")
    if "txo" in flags:
        command.append("-txo")
    if "rawtex" in flags:
        command.append("-rawtex")
    output = util.run_panda(ctx, *command)
    errored_files = ctx.regex_collection.not_found.findall(output)
    if errored_files:
        if not copy_errors(ctx, path, errored_files):
            return
        util.run_panda(ctx, "egg2bam", path, "-o", path.replace(".egg", ".bam"))

    if triplicate:
        build_lods(ctx, path.replace(".egg", ".bam"))


def bam2egg(ctx: util.Context, path: str) -> None:
    abspath, need_copy = pathlib.Path(path), False
    if not abspath.exists():
        abspath, need_copy = pathlib.Path(ctx.resources_path, path), True
    if not abspath.exists():
        raise Exception(f"Path {path} not found in the working directory or in the resource folder")

    if need_copy:
        copy(ctx.resources_path, ctx.working_path, path)

    output = util.run_panda(ctx, "bam2egg", path, "-o", path.replace(".bam", ".egg"))
    errored_files = ctx.regex_collection.not_found.findall(output)
    if not errored_files:
        logger.info("Recompilation not needed!")
        patch_egg(ctx, path.replace("bam", "egg"))
        return

    if not copy_errors(ctx, path, errored_files):
        return
    logger.info("Recompiling egg...")
    util.run_panda(ctx, "bam2egg", path, "-o", path.replace(".bam", ".egg"), debug=True)
    patch_egg(ctx, path.replace(".bam", ".egg"))


def build_lods(ctx: util.Context, path: str) -> None:
    if not path.endswith(".egg") and not path.endswith(".bam"):
        raise Exception("Only .egg and .bam files can be triplicated!")

    if any(f"{lod}." in path for lod in LODs):
        raise Exception("This file is already triplicated!")

    abspath = pathlib.Path(path)
    if not abspath.exists():
        raise Exception(f"Path {path} not found in the working directory")

    extension = path[-3:]
    base_name = path[:-4]
    target_names = [f"{base_name}{lod}.{extension}" for lod in LODs]
    for target_name in target_names:
        copy(ctx.working_path, ctx.working_path, path, target_name)
