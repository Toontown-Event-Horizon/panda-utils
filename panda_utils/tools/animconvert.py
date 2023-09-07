import logging

from panda_utils import util
from panda_utils.eggtree import eggparse, operations

logger = logging.getLogger("panda_utils.animconvert")


def animation_names(ctx: util.Context, path: str, output: str, conversion_names: dict[str, str]):
    eggpath = path.replace(".bam", ".egg")

    util.run_panda(ctx, "bam2egg", "-o", eggpath, path)
    logger.info("Converted file %s to egg, reading data...", path)

    with open(eggpath) as f:
        data = f.readlines()

    logger.info("Data read, converting names...")

    eggtree = eggparse.egg_tokenize(data)
    for node in eggtree.findall("Table"):
        if converted_name := conversion_names.get(node.node_name):
            logger.info("Converting %s to %s", node.node_name, converted_name)
            node.node_name = converted_name

    operations.add_comment(eggtree, "Toontown-Event-Horizon/PandaUtils Animation converter")
    logger.info("Finished converting names, creating new .bam file...")
    with open(eggpath, "w") as f:
        f.write(str(eggtree))

    util.run_panda(ctx, "egg2bam", "-o", output, eggpath)


def animation_rename_bulk(ctx: util.Context, path: str, output: str, conversion_names: dict[str, str]):
    for file in util.get_file_list(ctx.working_path, path):
        if file.endswith(".bam"):
            file = f"{path}/{file}"
            animation_names(ctx, file, file.replace(path, output), conversion_names)
