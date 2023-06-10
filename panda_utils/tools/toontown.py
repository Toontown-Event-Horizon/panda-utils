import logging

from panda_utils import util
from panda_utils.eggtree import eggparse, operations
from panda_utils.tools import convert

logger = logging.getLogger("panda_utils.toontown")


def toon_head(ctx: util.Context, path: str, triplicate: bool = False) -> None:
    util.run_panda(ctx, "egg-optchar", "-keepall", "-inplace", "-dart", "structured", path)

    with open(f"{ctx.working_path}/{path}") as f:
        data = f.readlines()

    eggtree = eggparse.egg_tokenize(data)
    operations.set_texture_prefix(eggtree, f"{util.toon_head_phase}/maps")

    nodes_for_removal = (
        eggtree.findall("Material")
        + eggtree.findall("MRef")
        + [scalar for scalar in eggtree.findall("Scalar") if scalar.node_name == "uv-name"]
    )
    eggtree.remove_nodes(set(nodes_for_removal))

    for uv in eggtree.findall("UV"):
        if uv.node_name == "UVMap":
            uv.node_name = None

    for eyes in eggtree.findall("Texture"):
        scalar_alpha_dual = eggparse.EggLeaf("Scalar", "alpha", "dual")
        eyes.add_child(scalar_alpha_dual)

    operations.add_comment(eggtree, "Toontown-Event-Horizon/PandaUtils ToonHead module")
    logger.info("Toon head successfully converted, building .bam file...")
    with open(f"{ctx.working_path}/{path}", "w") as f:
        f.write(str(eggtree))

    convert.egg2bam(ctx, path, triplicate=triplicate)
