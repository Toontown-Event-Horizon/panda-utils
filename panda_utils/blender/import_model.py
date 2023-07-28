import bpy
import sys

argv = sys.argv
argv = argv[argv.index("--") + 1 :]  # get all arguments after "--"

output_file, *input_files = argv


def import_model():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for file in input_files:
        if file.endswith("fbx"):
            bpy.ops.import_scene.fbx(filepath=file)
        elif file.endswith("obj"):
            bpy.ops.import_scene.obj(filepath=file)

    bpy.ops.wm.save_as_mainfile(filepath=output_file)


import_model()
