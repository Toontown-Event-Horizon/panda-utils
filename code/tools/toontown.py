from code import util
from code.eggtree import eggparse, operations


def toon_head(ctx: util.Context, path: str) -> None:
    util.run_panda(ctx, "egg-optchar", "-keepall", "-inplace", "-dart", "structured", path)

    with open(f"{ctx.working_path}/{path}") as f:
        data = f.readlines()

    eggtree = eggparse.egg_tokenize(data)
    operations.set_texture_prefix(eggtree, "phase_3/maps")

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
        if eyes.node_name == "eyes":
            scalar_alpha_dual = eggparse.EggLeaf("Scalar", "alpha", "dual")
            eyes.add_child(scalar_alpha_dual)

    operations.add_comment(eggtree, "Toontown-Event-Horizon/PandaUtils ToonHead module")
    print("Toon head successfully converted, building .bam file...")
    with open(f"{ctx.working_path}/{path}", "w") as f:
        f.write(str(eggtree))

    util.run_panda(ctx, "egg2bam", path, "-o", path.replace(".egg", ".bam"))
