import glob
import os

import bpy


def add_file(file_paths, file):
    file = file.replace(os.path.sep, "/")
    filename = file.split("/")[-1]
    file_paths[filename] = file


def locate_texture_files():
    file_paths = {}
    for extension in ("png", "rgb", "jpg", "gif"):
        for file in glob.glob(f"**/*.{extension}", recursive=True):
            add_file(file_paths, file)
    return file_paths


def update_texture_paths():
    texture_files = locate_texture_files()
    for mat in bpy.data.materials:
        if mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == "TEX_IMAGE":
                    img = node.image
                    if img is not None:
                        filename = img.filepath.replace(os.path.sep, "/").split("/")[-1]
                        old_path = img.filepath
                        img.filepath = "//" + os.path.relpath(texture_files.get(filename, filename))
                        if old_path != img.filepath:
                            print("Changed:", old_path, "->", img.filepath)


update_texture_paths()
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
