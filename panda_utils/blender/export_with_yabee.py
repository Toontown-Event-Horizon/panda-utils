import sys

import bpy
import addon_utils

argv = sys.argv
argv = argv[argv.index("--") + 1 :]  # get all arguments after "--"

output_file = argv[0]

# we need to find the module that exports eggs
modules = [
    mod
    for mod in addon_utils.modules()
    if mod.bl_info.get("description", "").lower().startswith("export to panda3d egg")
]

if len(modules) != 1:
    raise RuntimeError("YABEE not found or there are multiple copies")

yabee = addon_utils.enable(modules[0].__name__)
BAKE_LAYERS = {layer: (512, 512, False) for layer in ["diffuse", "normal", "gloss", "glow", "AO", "shadow"]}
bpy.ops.object.select_all(action="SELECT")

errors = yabee.egg_writer.write_out(
    output_file,
    {},  # animations dictionary
    False,  # "Export an animation for every action"
    False,  # "Export UV map as texture"
    True,  # "Write an animation data into the separate files"
    False,  # "Write only animation data"
    False,  # "Copy texture files together with EGG" -> default True in blender but not needed here bc we postprocess
    ".",  # texture path to use -> we postprocess
    "NO",  # "Export all textures as MODULATE or bake texture layers" -> NO TBS GEN
    "BAKE",  # "Export all textures as MODULATE or bake texture layers" -> NO MODULATE
    BAKE_LAYERS,
    False,  # "Merge meshes, armatured by single Armature"
    True,  # "Apply modifiers on exported objects (except Armature)"
    False,  # "Run pview after exporting"
    False,  # "Use loop normals created by applying 'Normal Edit' Modifier as vertex normals."
    False,  # "Export Physically Based Properties, requires the BAM Exporter",
    False,  # "when False, writes only vertex color if polygon material is using it "
)

# right now status code of blender is ignored, so we're not checking the errors XD
