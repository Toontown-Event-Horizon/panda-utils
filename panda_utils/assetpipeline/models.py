import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

import yaml
from panda_utils import util
from panda_utils.eggtree import eggparse, operations
from panda_utils.tools.convert import bam2egg, egg2bam
from panda_utils.util import get_data_file_path

preblend_regex = re.compile(r".*\.(fbx|obj)")
image_regex = re.compile(r".*\.(jpg|png|rgb)")
logger = logging.getLogger("panda_utils.pipeline.models")


def get_filename_regex(new_name):
    return re.compile(f"{new_name}(-[0-9]+)?.(jpg|png|rgb)")


def remap_texture_paths(tree, new_name):
    filename_regex = get_filename_regex(new_name)
    textures = tree.findall("Texture")
    remaps = {}
    counter = 0
    for texture in textures:
        texture_name = texture.get_child(0)
        texture_name_str = texture_name.value
        if texture_name_str[0] in '"\'':
            texture_name_str = texture_name_str[1:-1]
        if not filename_regex.match(texture_name_str):
            extension = texture_name_str.split(".")[-1]
            if counter == 0:
                new_texture_name = f"{new_name}.{extension}"
            else:
                new_texture_name = f"{new_name}-{counter}.{extension}"
            counter += 1
            remaps[texture_name_str] = new_texture_name
            texture_name.value = f'"{new_texture_name}"'

    return remaps


def action_preblend(ctx):
    count = 0
    for file in ctx.files:
        if preblend_regex.match(file):
            logger.info("%s: Converting to blend: %s", ctx.name, file)

            blend_filename = ctx.model_name
            if count:
                blend_filename += f"-{count}"
            blend_filename += ".blend"
            count += 1
            subprocess.run(
                ["blender", "--background", "--python", get_data_file_path("blender/import_model.py"),
                 "--", file, Path.cwd() / blend_filename],
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

    # The main thing we should do is patch the egg paths, thankfully panda-utils does that easily
    for file in ctx.files:
        if file.endswith(".egg"):
            logger.info("%s: Optimizing model: %s", ctx.name, file)
            with open(file) as f:
                data = f.readlines()

            eggtree = eggparse.egg_tokenize(data)
            renames = remap_texture_paths(eggtree, ctx.model_name)
            for fnold, fnnew in renames.items():
                shutil.move(fnold, fnnew)
                shutil.copy(fnnew, f"{ctx.output_texture}/{fnnew}")

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
                for index, node in enumerate(eggtree.children):
                    if isinstance(node, eggparse.EggBranch) and node.node_type == "Group":
                        new_node = eggparse.EggBranch("Group", ctx.model_name, [node])
                        eggtree.children[index] = new_node
                        break

            operations.set_texture_prefix(eggtree, f"{ctx.output_phase}/maps")
            with open(file, "w") as f:
                f.write(str(eggtree))


def action_transform(ctx):
    if "transforms.yml" in ctx.files:
        logger.info("%s: Loading transforms", ctx.name)
        with open("transforms.yml") as f:
            trdata = yaml.safe_load(f) or []
    else:
        return

    for file in ctx.files:
        if file.endswith(".egg"):
            logger.info("%s: Transforming: %s", ctx.name, file)
            options = []
            for transform in trdata:
                for key, value in transform.items():
                    transform_type = {"scale": "TS", "rotate": "TR", "translate": "TT"}[key]
                    options.append(f"-{transform_type}")
                    options.append(str(value))
            if options:
                translated_file_name = f"translated-{file}"
                util.run_panda(ctx.putil_ctx, "egg-trans", *options, "-o", translated_file_name, file)
                os.replace(translated_file_name, file)


def action_collide(ctx, flags="keep,descend", method="Sphere", group_name=None):
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


def action_egg2bam(ctx):
    files = []
    for file in ctx.files:
        if file.endswith(".egg"):
            logger.info("%s: Copying %s into the dist directory", ctx.name, file)
            shutil.copy(file, f"{ctx.output_model}/{file}")
            files.append(file)
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
