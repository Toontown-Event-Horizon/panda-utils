import os
import pathlib
import shutil
from typing import List

from code import util


def copy(source: str, target: str, path: str, target_fn: str = None) -> None:
    if target_fn is None:
        target_fn = path
    source_path = pathlib.Path(source, path)
    target_path = pathlib.Path(target, target_fn)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(source_path, target_path)


def patch_egg(ctx: util.Context, path: str) -> None:
    with open(f"{ctx.working_path}/{path}") as f:
        data = f.read()

    if ctx.working_path not in data:
        return

    data = data.replace(f"{ctx.working_path}/", "").replace(ctx.working_path, "")
    with open(f"{ctx.working_path}/{path}", "w") as f:
        f.write(data)
    print("Patched absolute source paths!")


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
    partial_abspath = ctx.resources_path + "/" + "/".join(path.split("/")[:-1])
    for x in errored_files:
        if os.path.exists(f"{ctx.resources_path}/{x}"):
            p2 = f"{ctx.resources_path}/{x}"
        elif os.path.exists(f"{partial_abspath}/{x}"):
            p2 = f"{partial_abspath}/{x}"
        else:
            p2 = input(f"Unable to find {x} in resources. Enter path to copy from: ")
            if not p2:
                print(f"Unable to get {x} from anywhere, aborting.")
                return False
        print(f"Copying {x} from resources.")
        target_path = p2.replace(ctx.resources_path, ctx.working_path)
        pathlib.Path(target_path).parent.mkdir(exist_ok=True, parents=True)
        shutil.copy(p2, target_path)

    return True


def egg2bam(ctx: util.Context, path: str, triplicate: bool = False) -> None:
    output = util.run_panda(ctx, "egg2bam", path, "-o", path.replace(".egg", ".bam"))
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
        print("Recompilation not needed!")
        patch_egg(ctx, path.replace("bam", "egg"))
        return

    if not copy_errors(ctx, path, errored_files):
        return
    print("Recompiling egg...")
    util.run_panda(ctx, "bam2egg", path, "-o", path.replace(".bam", ".egg"), debug=True)
    patch_egg(ctx, path.replace(".bam", ".egg"))


def build_lods(ctx: util.Context, path: str) -> None:
    if not path.endswith(".egg") or not path.endswith(".bam"):
        raise Exception("Only .egg and .bam files can be triplicated!")

    if any(f"-{lod}." in path for lod in (1000, 500, 250)):
        raise Exception("This file is already triplicated!")

    abspath = pathlib.Path(path)
    if not abspath.exists():
        raise Exception(f"Path {path} not found in the working directory")

    extension = path[-3:]
    base_name = path[:-4]
    target_names = [f"{base_name}-{lod}.{extension}" for lod in (1000, 500, 250)]
    for target_name in target_names:
        copy(ctx.working_path, ctx.working_path, path, target_name)
