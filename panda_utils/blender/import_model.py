import bpy
import sys

argv = sys.argv
argv = argv[argv.index("--") + 1:]  # get all arguments after "--"

input_file, output_file = argv


def import_model():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    if input_file.endswith("fbx"):
        bpy.ops.import_scene.fbx(filepath=argv[0])
    elif input_file.endswith("obj"):
        bpy.ops.import_scene.obj(filepath=argv[0])
    else:
        return

    bpy.ops.wm.save_as_mainfile(filepath=argv[1])


import_model()
