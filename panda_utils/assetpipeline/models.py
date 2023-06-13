import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

from panda_utils import util
from panda_utils.eggtree import eggparse, operations
from panda_utils.tools.convert import bam2egg, egg2bam
from panda_utils.tools.palettize import remove_palette_indices
from panda_utils.util import get_data_file_path

preblend_regex = re.compile(r".*\.(fbx|obj)")
logger = logging.getLogger("panda_utils.pipeline.models")


def build_asset_mapper(assets, name):
    output = {}
    for counter, item in enumerate(assets):
        extension = item.split(".")[-1]
        new_file_name = f"{name}-{counter}.{extension}" if counter else f"{name}.{extension}"
        output[item] = new_file_name
    return output


def get_all_textures(filename):
    textures = []
    with open(filename) as f:
        eggtree = eggparse.egg_tokenize(f.readlines())
    for tex in eggtree.findall("Texture"):
        textures.append(tex.get_child(0).value)
    return textures


def action_preblend(ctx):
    all_inputs = [file for file in ctx.files if preblend_regex.match(file)]
    logger.info("%s: Converting to blend: %s", ctx.name, ", ".join(all_inputs))

    blend_filename = f"{ctx.model_name}.blend"
    subprocess.run(
        ["blender", "--background", "--python", get_data_file_path("blender/import_model.py"),
         "--", Path.cwd() / blend_filename, *all_inputs],
        stdout=subprocess.DEVNULL,
        cwd=ctx.cwd,
    )


def action_blendrename(ctx):
    count = 0
    for file in ctx.files:
        if file.endswith(".blend"):
            blend_filename = ctx.model_name
            if count:
                blend_filename += f"-{count}"
            blend_filename += ".blend"
            count += 1
            shutil.move(file, blend_filename)


def action_blend2bam(ctx):
    for file in ctx.files:
        if file.endswith(".blend"):
            logger.info("%s: Patching texture paths: %s", ctx.name, file)
            full_path = f"{ctx.cwd}/{file}"
            subprocess.run(
                ["blender", full_path, "--background", "--python", get_data_file_path("blender/patch_paths.py")],
                stdout=subprocess.DEVNULL,
                cwd=ctx.cwd,
            )

            logger.info("%s: Converting to bam: %s", ctx.name, file)
            bam_filename = file[:-5] + "bam"
            res = subprocess.run(["blend2bam", "--no-srgb", file, bam_filename],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            err = res.stderr.decode("utf-8")
            if err and "KeyError: 'nodes'" in err:
                logger.error("%s: Blender output an empty model, aborting.", ctx.name)
                ctx.valid = False
            elif err:
                logger.error("%s: Blender failed", ctx.name)
                print(err)
                exit(1)


def action_bam2egg(ctx):
    for file in ctx.files:
        if file.endswith(".bam"):
            logger.info("%s: Converting %s from Bam to Egg", ctx.name, file)
            bam2egg(ctx.putil_ctx, file)


def action_optimize(ctx, mechanism):
    logger.info("%s: Using optimization mechanism: %s", ctx.name, mechanism)

    all_eggs = {}
    textures = set()
    for file in ctx.files:
        if file.endswith(".egg"):
            with open(file) as f:
                all_eggs[file] = tree = eggparse.egg_tokenize(f.readlines())
                for tex in tree.findall("Texture"):
                    textures.add(eggparse.sanitize_string(tex.get_child(0).value))

    texture_mapper = build_asset_mapper(textures, ctx.model_name)
    for fnold, fnnew in texture_mapper.items():
        shutil.move(fnold, fnnew)

    for file, eggtree in all_eggs.items():
        logger.info("%s: Optimizing model: %s", ctx.name, file)
        # The first thing we should do is patch the texture paths
        for tex in eggtree.findall("Texture"):
            tex_node = tex.get_child(0)
            tex_node.value = texture_mapper[eggparse.sanitize_string(tex_node.value)]

        # We also need to remove the default cube and the cameras if they're present in the model
        nodeset = set()
        for node in eggtree.children:
            if isinstance(node, eggparse.EggBranch) and node.node_type == "Group":
                if node.node_name == "Camera" or node.node_name.startswith("Cube."):
                    nodeset.add(node)
        eggtree.remove_nodes(nodeset)

        # For now we're also going to rename the top node into the model name, even though it's not
        # strictly correct to do
        if not any(group for group in eggtree.findall("Group") if group.node_name == ctx.model_name):
            group_node = eggparse.EggBranch("Group", ctx.model_name, [])
            removed_children = set()
            for node in eggtree.children:
                if isinstance(node, eggparse.EggBranch) and node.node_type == "Group":
                    group_node.children.append(node)
                    removed_children.add(node)

            eggtree.remove_nodes(removed_children)
            eggtree.children.append(group_node)

        with open(file, "w") as f:
            f.write(str(eggtree))


def action_transform(ctx, scale=None, rotate=None, translate=None):
    for file in ctx.files:
        if file.endswith(".egg"):
            logger.info("%s: Transforming: %s", ctx.name, file)
            options = []
            for value, transflag in [(scale, "-TS"), (rotate, "-TR"), (translate, "-TT")]:
                if value:
                    options.append(transflag)
                    options.append(str(value))
            if options:
                translated_file_name = f"translated-{file}"
                util.run_panda(ctx.putil_ctx, "egg-trans", *options, "-o", translated_file_name, file)
                os.replace(translated_file_name, file)


def action_collide(ctx, flags="keep,descend", method="sphere", group_name=None):
    group_name = group_name or ctx.model_name
    method = method.capitalize()
    flags = flags.replace(",", " ")
    for file in ctx.files:
        if file.endswith(".egg"):
            logger.info("%s: Adding collisions to %s: flags=%s method=%s", ctx.name, file, flags, method)

            with open(file) as f:
                data = f.readlines()

            eggtree = eggparse.egg_tokenize(data)
            groups = [group for group in eggtree.findall("Group") if group.node_name == group_name]
            if len(groups) == 1:
                logger.info("Found the named group!")
                new_node = eggparse.EggLeaf("Collide", group_name, f"{method} {flags}")
                groups[0].children.children.insert(0, new_node)

            with open(file, "w") as f:
                f.write(str(eggtree))


def action_palettize(ctx, palette_size="1024", flags=""):
    palette_size = int(palette_size)
    if palette_size & (palette_size - 1):
        raise ValueError("The palette size must be a power of two!")

    flag_list = flags.split(",")

    logger.info("%s: Creating a TXA file...", ctx.name)
    txa_text = (
        f":palette {palette_size} {palette_size}\n"
        ":imagetype png\n"
        ":powertwo 1\n"
        f":group {ctx.model_name} dir .\n"
        f"*.png : force-rgba dual linear clamp_u clamp_v margin 5\n"
    )
    with open("textures.txa", "w") as txa_file:
        txa_file.write(txa_text)

    all_eggs = [file for file in ctx.files if file.endswith(".egg")]

    logger.info("%s: Palettizing %s...", ctx.name, ', '.join(all_eggs))
    util.run_panda(
        ctx.putil_ctx,
        "egg-palettize",
        "-opt",
        "-redo",
        "-nodb",
        "-inplace",
        *all_eggs,
        "-inplace",
        "-tn",
        f"{ctx.model_name}_palette_%p_%i",
        timeout=60,
    )

    if "ordered" in flag_list:
        for file in all_eggs:
            remove_palette_indices(file)


def action_egg2bam(ctx):
    files = []
    for file in ctx.files:
        if file.endswith(".egg"):
            logger.info("%s: Copying %s into the dist directory", ctx.name, file)
            files.append(file)

            with open(file) as f:
                eggtree = eggparse.egg_tokenize(f.readlines())
            operations.set_texture_prefix(eggtree, f"{ctx.output_phase}/maps")
            for tex in eggtree.findall("Texture"):
                filename = eggparse.sanitize_string(tex.get_child(0).value).split("/")[-1]
                shutil.copy(filename, f"{ctx.output_texture}/{filename}")

            with open(file, "w") as f:
                f.write(str(eggtree))

            shutil.copy(file, f"{ctx.output_model}/{file}")

    os.chdir(ctx.output_model)
    os.chdir(ctx.putil_ctx.resources_path)
    ctx.putil_ctx.working_path = ctx.putil_ctx.resources_path
    for file in files:
        if file.endswith(".egg"):
            logger.info("%s: Converting %s to bam", ctx.name, file)
            egg2bam(ctx.putil_ctx, ctx.output_model_rel + "/" + file)
            os.unlink(f"{ctx.output_model}/{file}")
    os.chdir(ctx.cwd)
    ctx.putil_ctx.working_path = ctx.cwd
