import fnmatch
import logging
import os
import pathlib
import platform
import re
import shutil

from panda_utils import util
from panda_utils.assetpipeline.commons import AssetContext
from panda_utils.eggtree import eggparse, operations
from panda_utils.tools.convert import bam2egg, egg2bam
from panda_utils.tools.palettize import remove_palette_indices

image_regex = re.compile(r".*\.(png|jpg|rgb)")
logger = logging.getLogger("panda_utils.pipeline.models")
joint_regex = re.compile(r"^(.+)\[([xyzhprijkabc]+)]$")


def build_asset_mapper(assets, name):
    output = {}
    counter = 0
    for item in sorted(assets):
        if "_palette_" in item:
            continue

        extension = item.split(".")[-1]
        new_file_name = f"{name}-{counter}.{extension}" if counter else f"{name}.{extension}"
        output[item] = new_file_name
        counter += 1
    return output


def __patch_filename(filename):
    osname = platform.system()
    if osname == "Linux":
        return filename

    if osname == "Windows":
        if filename.startswith("/"):
            # /c/users/file.jpg -> C:\\users\\file.jpg
            return filename[1] + ":\\" + filename[3:].replace("/", "\\")

        return filename.replace("/", "\\")

    raise RuntimeError(f"Unsupported OS: {osname}")


def action_bam2egg(ctx: AssetContext):
    for file in ctx.files:
        if file.endswith(".bam"):
            logger.info("%s: Converting %s from Bam to Egg", ctx.name, file)
            bam2egg(ctx.putil_ctx, file)


def action_optimize(ctx: AssetContext, flags=""):
    if isinstance(flags, str):
        flags = flags.split(",")
    keep_texture_names = "keep_texture_names" in flags
    keep_uv_names = "keep_uv_names" in flags
    keep_transparent_vertices = "keep_transparent_vertices" in flags

    textures = set()
    ctx.cache_eggs()
    for tree in ctx.eggs.values():
        for tex in tree.findall("Texture"):
            textures.add(eggparse.sanitize_string(tex.get_child(0).value))

    texture_mapper = build_asset_mapper(textures, ctx.model_name) if not keep_texture_names else {}
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

            uvn = {s for s in tex.findall("Scalar") if s.node_name == "uv-name"}
            tex.remove_nodes(uvn)

        if not keep_uv_names:
            for v in eggtree.findall("Vertex"):
                for uv in v.findall("UV"):
                    uv.node_name = ""

        if not keep_transparent_vertices:
            logger.info("%s: Fixing transparent vertex colors: %s", ctx.name, file)
            for v in eggtree.findall("Vertex"):
                for rgb in v.findall("RGBA"):
                    color = rgb.node_value
                    if color == "0 0 0 0":
                        # For some reason (0, 0, 0, 0) is the default vertex color in blender. Which is wrong.
                        rgb.node_value = "1 1 1 1"

        # We also need to remove the default cube and the cameras if they're present in the model
        nodeset = set()
        for node in eggtree.children:
            if isinstance(node, eggparse.EggBranch) and node.node_type == "Group":
                if node.node_name == "Camera" or node.node_name.startswith("Cube."):
                    nodeset.add(node)
        eggtree.remove_nodes(nodeset)


def action_transparent(ctx: AssetContext):
    ctx.cache_eggs()
    for file, tree in ctx.eggs.items():
        logger.info("%s: Adding transparency to: %s", ctx.name, file)
        new_node = eggparse.EggLeaf("Scalar", "alpha", "dual")
        for tex in tree.findall("Texture"):
            for child in tex.children:
                if repr(child) == repr(new_node):
                    break
            else:
                tex.add_child(new_node)


def action_model_parent(ctx: AssetContext):
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


def action_transform(ctx: AssetContext, scale=None, rotate=None, translate=None):
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


def action_rmmat(ctx: AssetContext):
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


def action_collide(ctx: AssetContext, flags="keep,descend", method="sphere", group_name=None, bitmask=None):
    group_name = group_name or ctx.model_name
    method = method.capitalize()
    flags = flags.replace(",", " ")
    ctx.cache_eggs()
    for file, eggtree in ctx.eggs.items():
        logger.info("%s: Adding collisions to %s/%s: flags=%s method=%s", ctx.name, file, group_name, flags, method)
        groups = [group for group in eggtree.findall("Group") if group.node_name == group_name]
        if groups:
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
            # This was fixed in modern Panda3D versions but not everyone has updated to that
            nodes = groups[0].findall("Line") + groups[0].findall("Patch") + groups[0].findall("PointLight")
            if nodes:
                logger.warning("Found non-polygon objects while generating collisions, removing...")
                groups[0].remove_nodes(set(nodes))


def action_palettize(ctx: AssetContext, palette_size="1024", flags="", exclusions=""):
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
    )
    if isinstance(exclusions, str):
        exclusions = list(filter(None, exclusions.split(",")))

    all_png_files = [file for file in ctx.files if file.endswith(".png")]
    included_png_files, excluded_png_files = [], []
    for file in all_png_files:
        if any(fnmatch.fnmatch(file, exc) for exc in exclusions):
            excluded_png_files.append(file)
        else:
            included_png_files.append(file)

    if not included_png_files:
        raise RuntimeError("No images were included in the palette!")
    txa_text += " ".join(included_png_files) + " : force-rgba dual linear margin 5\n"
    if excluded_png_files:
        txa_text += " ".join(excluded_png_files) + " : omit\n"

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
        "-dm",
        "palette-temp",
        "-tn",
        f"{ctx.model_name}_palette_%p_%i",
        timeout=60,
    )

    if "ordered" in flag_list:
        for file in all_eggs:
            remove_palette_indices(file)

    logger.info("%s: Patching textures after palettization...", ctx.name)
    ctx.cache_eggs()
    for eggtree in ctx.eggs.values():
        for texture in eggtree.findall("Texture"):
            texture_name = texture.get_child(0)
            texture_name.value = texture_name.value.replace("palette-temp/", "", 1)
    palette_folder = pathlib.Path("palette-temp")
    for file in os.listdir(palette_folder):
        if "_palette_" in file:
            shutil.move(palette_folder / file, file)
    shutil.rmtree(palette_folder)


def action_optchar(ctx: AssetContext, flags="", expose="", zero=""):
    ctx.uncache_eggs()
    if isinstance(flags, str) and flags:
        flags = flags.split(",")
    if isinstance(expose, str) and expose:
        expose = expose.split(",")
    if isinstance(zero, str) and zero:
        temp_zero = zero.split(",")
        zero = []
        for joint in temp_zero:
            if m := joint_regex.match(joint):
                joint, coords = m.group(1), m.group(2)
                zero.append((joint, coords))
            else:
                zero.append((joint, ""))

    file = ctx.model_name + ".egg"
    main_file_processed = flags or expose
    animations_processed = zero

    if main_file_processed:
        if file in ctx.files:
            # Process the main model file.
            command = ["egg-optchar", file, "-inplace", "-keepall"]

            if flags:
                for flag in flags:
                    command.append("-flag")
                    command.append(flag)

            if expose:
                for joint in expose:
                    command.append("-expose")
                    command.append(joint)

            util.run_panda(ctx.putil_ctx, *command)

    if animations_processed:
        for eggfile in ctx.files:
            # Process the model's animations.
            if eggfile.endswith(".egg") and eggfile != file:
                command = ["egg-optchar", eggfile, "-inplace", "-keepall"]

                if zero:
                    for joint, coords in zero:
                        command.append("-zero")
                        command.append(joint + ("," + coords if coords else ""))

                util.run_panda(ctx.putil_ctx, *command)


def action_group_rename(ctx: AssetContext, **kwargs):
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


def action_group_remove(ctx: AssetContext, pattern):
    ctx.cache_eggs()
    for tree in ctx.eggs.values():
        removals = set()
        for group in tree.findall("Group"):
            if fnmatch.fnmatch(group.node_name, pattern):
                removals.add(group)

        tree.remove_nodes(removals)


def action_delete_vertex_colors(ctx: AssetContext):
    ctx.cache_eggs()
    for tree in ctx.eggs.values():
        for poly in tree.findall("Vertex"):
            poly.remove_nodes(poly.findall("RGBA"))


def action_uvscroll(ctx: AssetContext, group_name, speed_u="0", speed_v="0"):
    speed_u, speed_v = str(speed_u), str(speed_v)
    try:
        speed_u_val = float(speed_u)
        speed_v_val = float(speed_v)
    except ValueError:
        logger.error("%s: Invalid UV scroll: %s,%s", ctx.name, speed_u, speed_v)
        return

    if speed_u == speed_u_val and speed_v == speed_v_val:
        logger.error("%s: Both UV scroll speeds cannot be 0", ctx.name)
        return

    logger.info("%s: Applying uv scroll to %s", ctx.name, group_name)
    ctx.cache_eggs()
    for eggtree in ctx.eggs.values():
        # add uv scroll attribute
        groups = [g for g in eggtree.findall("Group") if g.node_name == group_name]
        if not groups:
            logger.error("%s: Did not find group with name: %s", ctx.name, group_name)
            return
        group = groups[0]

        if speed_u_val:
            scroll_u = eggparse.EggLeaf("Scalar", "scroll_u", speed_u)
            group.add_child(scroll_u)
        if speed_v_val:
            scroll_v = eggparse.EggLeaf("Scalar", "scroll_v", speed_v)
            group.add_child(scroll_v)


def action_egg2bam(ctx: AssetContext, flags="filter"):
    flags = flags.split(",")
    all_textures = "filter" not in flags

    files = []
    # if followed by palettize we wont have eggs here
    ctx.cache_eggs()

    copied_files = {}
    for file, eggtree in ctx.eggs.items():
        logger.info("%s: Copying %s into the dist directory", ctx.name, file)
        files.append(file)
        # don't have to do pathlib stuff here because egg files only use unix paths
        operations.set_texture_prefix(eggtree, ctx.output_texture_egg)
        for tex in eggtree.findall("Texture"):
            full_path = eggparse.sanitize_string(tex.get_child(0).value)
            filename = full_path.split("/")[-1]
            # The first two components of full_path we can safely ignore because they're phase_X/maps
            copied_files[filename] = pathlib.Path(pathlib.PurePosixPath(full_path.split("/", 2)[2]))

    if all_textures:
        # By default, we will be copying the textures into the `phase_X/maps/` folder
        # But if the egg file tells us to copy them into `phase_X/maps/subfolder/` then so be it
        for filename in ctx.files:
            if filename not in copied_files and image_regex.match(filename):
                copied_files[filename] = filename

    # Under no circumstances, we will be copying common texture set into the built/ folder.
    # This should be done by some other thing *before* we run the pipeline.
    copied_files = {cf: target for cf, target in copied_files.items() if cf not in ctx.copy_ignores}
    for filename, target in copied_files.items():
        copy_path = pathlib.Path(ctx.output_texture, target)
        copy_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(filename, copy_path)

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
            egg2bam(ctx.putil_ctx, str(pathlib.Path(ctx.output_model_rel, file)), flags=flags)
            os.unlink(pathlib.Path(ctx.output_model, file))
    os.chdir(ctx.cwd)
    ctx.putil_ctx.working_path = ctx.cwd
