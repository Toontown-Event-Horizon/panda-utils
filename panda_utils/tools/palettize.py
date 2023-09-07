import logging
import os
import pathlib
import shutil

from panda_utils import util
from panda_utils.eggtree import eggparse

logger = logging.getLogger("panda_utils.palettize")


def remove_palette_indices(egg_path):
    with open(egg_path) as f:
        data = f.readlines()

    eggtree = eggparse.egg_tokenize(data)
    all_groups = eggtree.findall("Group")
    for group in all_groups:
        if "-" not in group.node_name:
            continue

        name_split = group.node_name.split("-", 1)
        try:
            int(name_split[0])
        except ValueError:
            continue
        else:
            group.node_name = name_split[1]

    with open(egg_path, "w") as f:
        f.write(str(eggtree))


def palettize(
    ctx: util.Context, output: str, phase: str, subdir: str, poly: int = None, margin: int = 0, ordered: bool = False
) -> None:
    map_path, model_path = f"{phase}/maps", f"{phase}/models/{subdir}"
    pathlib.Path(map_path).mkdir(exist_ok=True, parents=True)
    pathlib.Path(model_path).mkdir(exist_ok=True, parents=True)

    file_list = set(util.get_file_list(ctx.resources_path, f"{map_path}/{output}"))
    existing_file_list = set(util.get_file_list(ctx.working_path, f"{map_path}/{output}"))
    logger.info("Found %d files, copying to the workspace...", len(file_list - existing_file_list))
    for x in file_list:
        if not os.path.exists(f"{ctx.working_path}/{map_path}/{output}/{x}"):
            shutil.copy(f"{ctx.resources_path}/{map_path}/{output}/{x}", f"{ctx.working_path}/{map_path}/{output}/{x}")
    logger.info("Running egg-texture-cards...")
    egg_path = f"{model_path}/{output}.egg"
    union = file_list.union(existing_file_list)
    args = ["-o", egg_path]
    if poly:
        args += ["-p", f"{poly},{poly}"]
    args += [f"{map_path}/{output}/{x}" for x in union]
    util.run_panda(ctx, "egg-texture-cards", *args)

    logger.info("Creating a TXA file...")
    # txa_text = self.create_txa(2048, file_list)
    txa_text = (
        ":palette 2048 2048\n"
        ":imagetype png\n"
        ":powertwo 1\n"
        f":group {output} dir {phase}/maps\n"
        f"*.png : force-rgba dual linear clamp_u clamp_v margin {margin}\n"
    )
    with open("textures.txa", "w") as txa_file:
        txa_file.write(txa_text)

    logger.info("Palettizing...")
    util.run_panda(
        ctx,
        "egg-palettize",
        "-opt",
        "-redo",
        "-noabs",
        "-nodb",
        "-inplace",
        egg_path,
        "-dm",
        map_path,
        "-tn",
        f"mk2_{output}_palette_%p_%i",
        timeout=60,
    )
    logger.info("Transforming eggs...")
    util.run_panda(ctx, "egg-trans", egg_path, "-pc", map_path, "-o", egg_path)

    if ordered:
        logger.info("Removing ordering indices from the egg...")
        remove_palette_indices(egg_path)

    logger.info("Converting to BAM...")
    util.run_panda(ctx, "egg2bam", egg_path, "-o", egg_path.replace(".egg", ".bam"), timeout=10)
    logger.info("Cleaning up...")
    shutil.rmtree(f"{model_path}/{phase}", ignore_errors=True)  # happens due to a bug
    # os.unlink(egg_path)
    os.unlink("textures.txa")
    logger.info("Palettizing complete.")
