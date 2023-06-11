# Panda3D Utils v1.1
 
This repository includes multiple tools for some basic Panda3D automation. Written in Python.

## Installation
* `pip install panda_utils`
* This package includes a number of optional dependencies:
  * `pip install panda_utils[imagery]` to enable the Downscale module
  * `pip install panda_utils[autopath]` to automatically download P3D
  * `pip install panda_utils[runnable]` to enable the CLI runner
    * Requires a settings file to be used that way, see: `config_example.ini`
      in this repository
  * `pip install panda_utils[pipeline]` to enable the Pipeline runner
  * `pip install panda_utils[everything]` to include all of the above

## Features
* Advanced `bam2egg` unpacker
  * Normally, Panda3D's `bam2egg` does not work if a texture in the model was deleted.
  Even if `-noexist` argument is passed. I suspect this is a bug.
  * Additionally, it means you would have to unpack the bam file in your working
  directory, which is bad on production for multiple reasons I'm not going to explain.
  * This script tries to unpack bam files. If a file is not present, it either grabs
  it from the production, and if it's not present there either you can set a fallback
  file location. Useful when you rename maps for some reason.
  * Saves the egg file in the same directory as bam file with the same name.
  * Run: `python main.py bam2egg <path_to_bam_file>`
* Automatic palettizer
  * Palettizing is merging multiple images into one palette, a larger image containing
  spritesheets. Good for performance.
  * Panda3D has a palettizer, but it's not trivial to make work manually for various
  reasons. The documentation is lacking, absolute paths are a problem (even with
  `-noabs`, surprisingly), some amount of manual work is involved, and it bloats
  the environment as well.
  * Currently, only creating palettes of images within one model is supported.
  * Run: `python main.py palettize <directory_name> <phase_folder> <model_type> <pattern>`
    * The explanation below assumes your images are located in
    `resources/phase_6/maps/guns`.
    * `directory_name` is the directory containing the images, i.e. `guns`.
    * `phase_folder` is `phase_6` in this scenario, `model_type` is probably `props`.
    * The palette will be saved under `resources/phase_6/maps`,
    and the model under `resources/phase_6/model/props`. The initial images can be
    safely removed after running.
    * `pattern` is optional and defaults to `*`. Right now it can either be `*` or the
    list of file names (i.e. `"water_gun.png fire_thrower.png laser.png"`). Self-explanatory.
  * Can use files from under working directory as well as the resource
  directory. Uses the working directory by default, delete or rename files
  to load the original ones.
  * Additional parameters:
    * `-p, --poly`: Set the pixel size per 1x1 node. Useful when palettizing related
    images of different sizes, such as UI elements. By default, all images palettized
    will be 1x1 in the scene graph.
    * `-m, --margin`: Set the margin around the palettized image to prevent image
    bleeding. Defaults to 0.
* Automatic downscaler
  * Many times, assets are made in high resolution, and then have to be downscaled to
  a smaller one - 512x512 or 256x256.
  * Doing this by hand is a tedious process. This script can do it automatically.
  * By default, only perfectly square images are processed. `--force` can be used to
  process rectangular images with a small accuracy loss.
  * By default, force-rescaled images with higher width than height are moved to
  the bottom of the square version. To prevent this, use `--truecenter`.
  * `--bbox=<number>` allows to automatically crop the images to their bounding box,
  to prevent downscaling images with large spaces. `10` is the recommended number,
  the higher it is the more space will be left on sides. Disabled by default.
  * Run: `python main.py downscale <directory_path> <64|128|256|512|1024>`
* Model fixing pipeline
  * Sometimes models made a long time ago do not have correct binormals and can't be shaded
  correctly. Attempting to manually add binormals often breaks the rig of the model.
  * This script can automatically fix models' binormals. Not a 100% working process,
  but works most of the time.
  * In addition, fixes any absolute texture paths found in the model.
  * Run: `python main.py pipeline <path_to_bam>`
* Toon head exporting
  * While Panda3D has a lot of quirks with model loading, toon heads are notoriously
  known as ones causing many issues. This script can convert them to the format that works.
  * Requires exporting models to `egg` first. `yabee` mostly works for that if using Blender.
  * Run: `python main.py toonhead <path_to_egg>`
  * The procedure is due to DTM1218, I merely reimplemented it using a Syntax Tree 
  instead of regexes.
* Smaller utilities
  * Add binormals to an egg file: `python main.py egg-trans <path_to_egg>`
  * Fix absolute tex paths in an egg file: `python main.py patch <path_to_egg>`
  * Copy a file from/to workspace to/from the resources folder: `python main.py copy <path_to_egg>`
    * Defaults to copying from the workspace to the resources folder. 
    * `-r`, `--reverse`: copies from resources to the workspace.

## Programmatical usage
Panda-Utils can be used programmatically. For any operations, a context must be
created. The easiest way to create a context is by calling `from_config`:

```python
from panda_utils.util import Context

ctx = Context.from_config({
  "paths": {"resources": "path/to/resources/folder",
            "panda": "path/to/panda/installation/bin"}
})
```

Instead of providing the Panda3D path directly, you can inherit it from the
Python site_packages path:


```python
from panda_utils.util import Context

ctx = Context.from_config({
  "paths": {"resources": "path/to/resources/folder"},
  "options": {"panda3d_path_inherit": True}
})
```

This requires Panda3D to be installed in the same venv with this package.

## Asset Pipeline

Panda-Utils provides an asset pipeline script that can be used to build
game-ready BAM models from models in other formats (FBX/Blend/etc.) Note that
this process is not complete and is going to be extended in the future.
This can be used manually through scripts, and also supports batch processing
(for example, through Makefiles). Parallel execution works as well, as long
as no two models have the same model name.

The pipeline can be started through:
```shell
python -m panda_utils.assetpipeline path/to/input_folder {phase_X} {category} [step1] [step2] [...]
```

Most of the time, the script expects a following directory structure:
```
input_folder
    model.fbx (or model.blend etc., depending on the options)
    texture.png
    texture-names-dont-matter.png
    formats-dont-matter-either.jpg
    ...
```

This will put a compiled model into `built/phase_X/{category}/input_folder.bam`
and the texture into `built/phase_X/maps/input_folder.png` (or jpg, or rgb). If
the model uses multiple textures, they will be named `input_folder.png`,
`input_folder-1.png`, etc.

Running the pipeline creates a folder `intermediate` with various build files.
They can be safely removed after the pipeline ends, and can also be used to
inspect the correctness of various steps.

Since all changes are done in the intermediate folder, the contents of the
input folder will not change after running this script, meaning the input
folder can be committed into version control.

Each step includes a step name and optionally arguments to that step, colon-separated.
For example, `step_name:arg1:arg2` will call the step `step_name` with the arguments
`arg1` and `arg2`. The steps are called in order from left to right.
The list of all currently existing steps is below.

### Preblend

This step will convert OBJ or FBX models into BLEND. It requires installing
Blender on the machine. Note that due to specifics of various modeling software,
the model may end up scaled incorrectly at this phase. You can use the `transform`
step to fix this. This step takes no arguments.

`preblend`

### BlendRename

This step will rename the BLEND models into their proper name. It is required
if the input files are in BLEND format, but not required if the Blend files are
generated through Preblend. This step takes no arguments.

`blendrename`

### Blend2Bam

This step will use Blend2Bam to convert the BLEND moodels into an intermediate
BAM model. It should happen after `preblend` or `blendrename`. This model
is usually not suitable for ingame use and requires further processing through
`bam2egg`. This step requires installing Blender on the machine. It is tested
with Blender 3.5.1, but is likely to work on other versions as well.

This is currently using the GLTF pipeline (available since Blender 2.8),
the builtin physics system (not bullet), and disables sRGB textures due to 
specifics of Toontown use. It takes no arguments, but these things 
might become configurable later through optional arguments.

`blend2bam`

### Bam2Egg

This step will decompile every BAM model into EGG models, which are used
for processing through other methods. It takes no arguments.

`bam2egg`

### Optimize

This step will do the following transformations to every EGG model it finds:

* Remaps texture paths so they work with the desirred directory structure.
  This requires that the texture paths in the model are flat, i.e. they're
  relative and point to a file in the same directory. `Blend2Bam` will
  perform that conversion automatically, but if a different step is used
  this has to be done separately.
* Removes the default cube `Cube.N` and camera `Camera` groups from the file
  if they're found inside.
* Creates a group with the same name as the model name, containing everything
  inside of the model. This is useful if the Panda3D code is using `find()`
  while loading this model.

This function takes one required parameter `profile`. However, the profile
is currently ignored. In the future, there will be multiple profiles that can
(for example) run egg-optchar, etc.

`optimize:stiffchar`
`optimize:actorchar`
`optimize:prop`

### Transform

This step looks for a file named `transforms.yml` in the input directory.
It will then apply the given transforms to every egg file it encounters.
An example file can look like this:

```yaml
- scale: 10
- rotate: 0,0,180
- translate: 0,-0.25,1
```

This will first increase the model scale 10 times, then rotate it 180 degrees
around the Z axis (functionally setting its H angle to 180), and then translate
it 1 unit upwards and 0.25 units backwards.

This step takes no arguments. This loading method was chosen to automatically
support batch processing through Makefiles.

`transform`

### Collide

This step will automatically add collision geometry to a model. This step
will not automatically make decimated collision geometry, that has to be done
separately. It can either add preset geometry types like Sphere, or Polyset
geometry for complex shapes. Note that adding Polyset collisions is
computationally expensive for the players of the game and having a decimated
model for polysets is recommended.

This step takes three arguments:
* `flags`: comma-separated list of Egg collision flags. Defaults to `keep,descend`.
* `method`: lowercase type of the collider (sphere, polyset, etc.)
  Defaults to `sphere`, which is undesired in most cases.
* `group_name`: If supplied, the collision will be added to a node with
  the given name. If not supplied (default), the collision will be added
  to a node with the name = input_folder's name (this group is automatically
  created by the optimize step).

This step can appear multiple times in the pipeline if one wants to add
multiple collision solids to different parts of the model. 

`collide`
`collide:keep,descend:tube`
`collide:descend:polyset:optimized_geom`

### Egg2Bam

This step is used to assemble the EGG model into the BAM model suitable
for ingame use. It also copies the model into `built` folder. It takes no
arguments.

`egg2bam`

### Script

This step can be used to run scripts that are not packaged with this project.
The script will run in the directory including (transformed versions of) all
assets in the input directory. It will receive the name of the model as its only
argument. This step includes one parameter with the path to the script. Note that
due to the specifics of implementation, it has to be the path, but the type
of the script is not limited (shell, python, etc.) as long as it's an executable.

`script:scripts/magic.sh`

For example, if your directory structure looks like this:

```
inputs
  asset_name
    model.blend
    texture.png
scripts
  magic.sh (needs an executable flag)
```

The pipeline would be invoked like this:

```shell
python -m panda_utils.assetpipeline inputs/asset_name asset char script:scripts/magic.sh
```

## Future plans
* Reverse palettizing based on the image coordinates
* Automatic decimation in the Asset Pipeline for collision purposes
* Addition of palettize functionality into the Asset Pipeline
* Addition of toon head functionality into the Asset Pipeline
