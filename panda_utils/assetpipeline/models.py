import fnmatch
import logging
import os
import pathlib
import platform
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
image_regex = re.compile(r".*\.(png|jpg|rgb)")
logger = logging.getLogger("panda_utils.pipeline.models")


def run_blender(cwd, file, script, *inputs):
    args = [util.choose_binary("blender"), "--background", "--python", get_data_file_path(script), "--", *inputs]
    if file is not None:
        args.insert(1, file)
    stdout_pipe = subprocess.DEVNULL if not os.getenv("PANDA_UTILS_BLENDER_LOGGING") else None
    subprocess.run(args, stdout=stdout_pipe, cwd=cwd)


def build_asset_mapper(assets, name):
    output = {}
    for counter, item in enumerate(sorted(assets)):
        extension = item.split(".")[-1]
        new_file_name = f"{name}-{counter}.{extension}" if counter else f"{name}.{extension}"
        output[item] = new_file_name
    return output


def __patch_filename(filename):
    osname = platform.system()
    if osname == "Linux":
        return filename

    if osname == "Windows":
        return filename[1] + ":\\" + filename[3:].replace("/", "\\")

    raise RuntimeError(f"Unsupported OS: {osname}")


def action_preblend(ctx):
    all_inputs = [file for file in ctx.files if preblend_regex.match(file)]
    logger.info("%s: Converting to blend: %s", ctx.name, ", ".join(all_inputs))

    blend_filename = f"{ctx.model_name}.blend"
    run_blender(ctx.cwd, None, "blender/import_model.py", Path.cwd() / blend_filename, *all_inputs)


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


def __run_export_util(ctx, binary, input_file, output_file, flags):
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


def __run_blend2bam(ctx, file, flags):
    logger.info("%s: Patching texture paths: %s", ctx.name, file)
    full_path = f"{ctx.cwd}/{file}"
    run_blender(ctx.cwd, full_path, "blender/patch_paths.py")

    logger.info("%s: Converting to bam: %s", ctx.name, file)
    bam_filename = file[:-5] + "bam"
    __run_export_util(ctx, "blend2bam", file, bam_filename, flags)


def __run_gltf2bam(ctx, file, flags):
    logger.info("%s: Exporting to GLTF: %s", ctx.name, file)
    full_path = f"{ctx.cwd}/{file}"
    intermediate_file = file[:-5] + "glb"
    bam_filename = file[:-5] + "bam"
    target_path = f"{ctx.cwd}/{intermediate_file}"
    run_blender(ctx.cwd, full_path, "blender/export_glb.py", target_path)

    logger.info("%s: Converting to bam: %s", ctx.name, intermediate_file)
    __run_export_util(ctx, "gltf2bam", intermediate_file, bam_filename, flags)


def action_blend2bam(ctx, flags=""):
    flags = flags.lower().split(",")
    for file in ctx.files:
        if file.endswith(".blend"):
            if "b2b" in flags:
                __run_blend2bam(ctx, file, flags)
            else:
                __run_gltf2bam(ctx, file, flags)


def action_bam2egg(ctx):
    for file in ctx.files:
        if file.endswith(".bam"):
            logger.info("%s: Converting %s from Bam to Egg", ctx.name, file)
            bam2egg(ctx.putil_ctx, file)


def action_yabee(ctx):
    for file in ctx.files:
        if file.endswith(".blend"):
            logger.info("%s: Exporting through YABEE: %s", ctx.name, file)
            full_path = f"{ctx.cwd}/{file}"
            run_blender(ctx.cwd, full_path, "blender/export_with_yabee.py", file[:-6] + ".egg")


def action_optimize(ctx, map_textures="true"):
    map_textures = map_textures.lower() not in ("", "0", "false")

    textures = set()
    ctx.cache_eggs()
    for tree in ctx.eggs.values():
        for tex in tree.findall("Texture"):
            textures.add(eggparse.sanitize_string(tex.get_child(0).value))

    texture_mapper = build_asset_mapper(textures, ctx.model_name) if map_textures else {}
    for fnold, fnnew in texture_mapper.items():
        fnold = __patch_filename(fnold)
        shutil.move(fnold, fnnew)

    for file, eggtree in ctx.eggs.items():
        logger.info("%s: Optimizing model: %s", ctx.name, file)
        # The first thing we should do is patch the texture paths
        for tex in eggtree.findall("Texture"):
            tex_node = tex.get_child(0)
            old_value = eggparse.sanitize_string(tex_node.value)
            tex_node.value = texture_mapper.get(old_value, old_value)

        # We also need to remove the default cube and the cameras if they're present in the model
        nodeset = set()
        for node in eggtree.children:
            if isinstance(node, eggparse.EggBranch) and node.node_type == "Group":
                if node.node_name == "Camera" or node.node_name.startswith("Cube."):
                    nodeset.add(node)
        eggtree.remove_nodes(nodeset)


def action_transparent(ctx):
    ctx.cache_eggs()
    for file, tree in ctx.eggs.items():
        logger.info("%s: Adding transparency to: %s", ctx.name, file)
        new_node = eggparse.EggLeaf("Scalar", "alpha", "dual")
        for tex in tree.findall("Texture"):
            for child in tex.children:
                if child.equals(new_node):
                    break
            else:
                tex.add_child(new_node)


def action_model_parent(ctx):
    ctx.cache_eggs()
    for eggtree in ctx.eggs.values():
        if not any(group for group in eggtree.findall("Group") if group.node_name == ctx.model_name):
            group_node = eggparse.EggBranch("Group", ctx.model_name, [])
            removed_children = set()
            for node in eggtree.children:
                if isinstance(node, eggparse.EggBranch) and node.node_type == "Group":
                    group_node.children.append(node)
                    removed_children.add(node)

            eggtree.remove_nodes(removed_children)
            eggtree.children.append(group_node)


def action_transform(ctx, scale=None, rotate=None, translate=None):
    ctx.uncache_eggs()
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


def action_rmmat(ctx):
    ctx.cache_eggs()
    for file, eggtree in ctx.eggs.items():
        logger.info("%s: Removing materials from: %s", ctx.name, file)
        nodes_for_removal = (
            eggtree.findall("Material")
            + eggtree.findall("MRef")
            + [scalar for scalar in eggtree.findall("Scalar") if scalar.node_name == "uv-name"]
        )
        eggtree.remove_nodes(set(nodes_for_removal))

        for uv in eggtree.findall("UV"):
            uv.node_name = None


def action_collide(ctx, flags="keep,descend", method="sphere", group_name=None, bitmask=None):
    group_name = group_name or ctx.model_name
    method = method.capitalize()
    flags = flags.replace(",", " ")
    ctx.cache_eggs()
    for file, eggtree in ctx.eggs.items():
        logger.info("%s: Adding collisions to %s/%s: flags=%s method=%s", ctx.name, file, group_name, flags, method)
        groups = [group for group in eggtree.findall("Group") if group.node_name == group_name]
        if len(groups) == 1:
            logger.info("Found the named group!")
            new_node = eggparse.EggLeaf("Collide", group_name, f"{method} {flags}")
            group_children = groups[0].children.children
            group_children.insert(0, new_node)

            if bitmask is not None:
                mask_hex = f"{bitmask:#010x}"
                bitmask_node = eggparse.EggLeaf("Scalar", "collide-mask", mask_hex)
                group_children.insert(1, bitmask_node)

            # Fun fact: Setting <Collide> if the group has non-poly objects will cause a segfault
            # when the egg file is read. So we have to delete every object that's not a polygon.
            # https://github.com/panda3d/panda3d/issues/1515
            nodes = groups[0].findall("Line") + groups[0].findall("Patch") + groups[0].findall("PointLight")
            if nodes:
                logger.warning("Found non-polygon objects while generating collisions, removing...")
                groups[0].remove_nodes(set(nodes))


def action_palettize(ctx, palette_size="1024", flags=""):
    ctx.uncache_eggs()
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

    logger.info("%s: Palettizing %s...", ctx.name, ", ".join(all_eggs))
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


def action_optchar(ctx, flags, expose):
    ctx.uncache_eggs()
    if isinstance(flags, str):
        flags = flags.split(",")
    if isinstance(expose, str):
        expose = expose.split(",")

    for file in ctx.files:
        if file.endswith(".egg"):
            command = ["egg-optchar", file, "-inplace", "-keepall"]

            for flag in flags:
                command.append("-flag")
                command.append(flag)

            for joint in expose:
                command.append("-expose")
                command.append(joint)

            util.run_panda(ctx.putil_ctx, *command)


def action_group_rename(ctx, **kwargs):
    ctx.cache_eggs()
    for tree in ctx.eggs.values():
        removals = set()
        for group in tree.findall("Group"):
            if new_name := kwargs.get(group.node_name):
                if new_name == "__delete__":
                    removals.add(group)
                else:
                    group.node_name = new_name

        tree.remove_nodes(removals)


def action_group_remove(ctx, pattern):
    ctx.cache_eggs()
    for tree in ctx.eggs.values():
        removals = set()
        for group in tree.findall("Group"):
            if fnmatch.fnmatch(group.node_name, pattern):
                removals.add(group)

        tree.remove_nodes(removals)


def action_egg2bam(ctx, all_textures=""):
    all_textures = all_textures.lower() not in ("", "0", "false")

    files = []
    # if followed by palettize we wont have eggs here
    ctx.cache_eggs()

    copied_files = set()
    for file, eggtree in ctx.eggs.items():
        logger.info("%s: Copying %s into the dist directory", ctx.name, file)
        files.append(file)
        operations.set_texture_prefix(eggtree, f"{ctx.output_phase}/maps")
        for tex in eggtree.findall("Texture"):
            filename = eggparse.sanitize_string(tex.get_child(0).value).split("/")[-1]
            copied_files.add(filename)

    if all_textures:
        copied_files.clear()
        for filename in ctx.files:
            if image_regex.match(filename):
                copied_files.add(filename)

    copied_files = {cf: ctx.path_overrides.get(cf) for cf in copied_files}
    delete_paths = set()
    delete_parents = set()
    for filename, target_path in copied_files.items():
        if target_path is None:
            copy_path = pathlib.Path(ctx.output_texture, filename)
        else:
            copy_path = pathlib.Path(ctx.output_texture, target_path, filename)
        copy_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(filename, copy_path)
        if filename in ctx.post_remove:
            delete_paths.add(copy_path)
            delete_parents.add(copy_path.parent)

    ctx.uncache_eggs()
    for file in ctx.files:
        if file.endswith(".egg"):
            shutil.copy(file, pathlib.Path(ctx.output_model, file))

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
    for dp in delete_paths:
        os.unlink(dp)
    for folder in delete_parents:
        ctx.reverse_rmdir(folder)
