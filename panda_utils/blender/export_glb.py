import sys

import bpy

argv = sys.argv
argv = argv[argv.index("--") + 1 :]  # get all arguments after "--"

output_file = argv[0]
bpy.ops.export_scene.gltf(filepath=output_file, check_existing=False, export_keep_originals=True)
