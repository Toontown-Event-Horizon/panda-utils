import os
import sys

import bpy

argv = sys.argv
argv = argv[argv.index("--") + 1 :]  # get all arguments after "--"

output_file = argv[0]


def update_texture_paths():
    for mat in bpy.data.materials:
        if mat.use_nodes:
            for node in mat.node_tree.nodes:
                if node.type == "TEX_IMAGE":
                    img = node.image
                    if img is not None:
                        img.filepath = img.filepath.replace(os.path.sep, "/").split("/")[-1]


update_texture_paths()
bpy.ops.export_scene.gltf(filepath=output_file, check_existing=False, export_keep_originals=True)
