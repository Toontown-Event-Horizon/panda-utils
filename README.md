# Panda3D Utils v1.3
 
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

*NOTE: the pipeline is currently in an unstable state. Expect the API to break
a lot.*

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

Any step accepting arguments can be called with `step_name[]` without any arguments.
In that case, the step will take the arguments from a YAML file named `model-config.yml`
in the asset input directory. It is parsed as follows:

* First, the yaml field with the name = the step name is taken from the file.
* If that field is not present, or the file is not present, the step has
  no effect.
* If the field is a dictionary, it will be applied as keyword arguments.
* If the field is a list, the step will be applied once for each dictionary
  inside of it in the proper order.

This sounds confusing, so here's an example of such a config file:

```yaml
transform:
  - scale: 10
  - rotate: 0,0,180
collide:
  flags: keep,descend
  method: polyset
  group_name: optimized
```

When a `transform[]` action is encountered, two transform steps will be called
in order, first the node will be rescaled, and then it will be rotated.
When a `collide[]` action is encountered, it will be called once with the given
arguments. If a different `[]` action is encountered, it will not run.
This method is used for easy interaction with Makefiles (if the input folder 
is set as the makefile dependency, changing this file will cause the task
building a given asset to be rerun).

The pipeline will normally hide all outputs unless the environmental variable
`PANDA_UTILS_LOGGING`  is not empty.

The list of all currently existing steps is below.

### Preblend

This step will convert OBJ or FBX models into BLEND. It requires installing
Blender on the machine. Note that due to specifics of various modeling software,
the model may end up scaled incorrectly at this phase. You can use the `transform`
step to fix this. All OBJ and FBX files will be joined into the same file.
This step takes no arguments.

**Changelog**
* 1.2 - now joins all models into the same blend file, instead of making
  separate blend files per model
* 1.1 - initial implementation

**Examples**
`preblend`

### BlendRename

This step will rename the BLEND models into their proper name. It is required
if the input files are in BLEND format, but not required if the Blend files are
generated through Preblend. This step takes no arguments.

**Changelog**
* 1.1 - initial implementation

**Examples**
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

**Changelog**
* 1.1 - initial implementation

**Examples**
* `blend2bam`

### Bam2Egg

This step will decompile every BAM model into EGG models, which are used
for processing through other methods. It takes no arguments.

**Changelog**
* 1.1 - initial implementation

**Examples**
* `bam2egg`

### Optimize

This step will do the following transformations to every EGG model it finds:

* Removes the default cube `Cube.N` and camera `Camera` groups from the file
  if they're found inside.
* Renames all textures to follow a consistent naming pattern. For example,
  if textures `file1.png`, `Randomfile.jpg` and `otherFile.png` are provided,
  they will be renamed into `input_folder.png`, `input_folder-1.jpg` and
  `input_folder-2.png` (the order is not guaranteed, but it will be consistent
  if this step is launched multiple times).

This function takes no parameters.

**Changelog**
* 1.3 - no longer takes parameters, no longer sets model parents
  (see: `model_parent`)
* 1.2 - no longer changes the texture path prefix (now done by egg2bam)
* 1.1 - initial implementation

**Examples**
* `optimize`

### Model Parent
This step creates a group with the same name as the model name, containing
the entire model inside itself. This can be useful if the Panda3D code is using
`find()` while loading this model.

This step takes no parameters.

**Changelog**
* 1.3 - initial implementation

*Examples**
* `model_parent`

### Group rename
This step renames all collections with the given name into a different name.

This step uses keyword arguments, which means it can only be run through `[]`.
Setting a name to `__delete__` will delete the node. For example:

```yaml
group_rename:
  hands.003: hands
  useless-node: __delete__
```

**Changelog**
* 1.3 - initial implementation

*Examples**
* `group_rename[]`

### Group remove
This step removes all collections with the given name. Unlike group rename,
allows using fnmatch syntax to find the collections.

Accepts one argument equal to the fnmatch pattern that is removed. Can be
run multiple times if desired.

```yaml
group_rename:
  hands.003: hands
  useless-node: __delete__
```

**Changelog**
* 1.3 - initial implementation

*Examples**
* `group_remove[]`
* `group_remove:*useless*`

### Optchar
This step runs `egg-optchar`, setting the exposed joints and the flagged nodes.
Note that changing the dart is currently not supported.

This model takes two parameters. Both of them can be comma-separated strings,
or lists of strings (only if the `[]` syntax is used). The first parameter is
the flagged nodes, the second parameter is the exposed joints.

**Changelog**
* 1.3 - initial implementation

**Examples**
* `optchar[]`
* `optchar:this-node-has-texture-set:joint_whatever`

### Transform

This step will apply the given transforms to every egg file it encounters.
Each transform is a combination of scale, rotate, and translate. For example:

* `transform:10:0,0,180:0,-0.25,1`

This will first increase the model scale 10 times, then rotate it 180 degrees
around the Z axis (functionally setting its H angle to 180), and then translate
it 1 unit upwards and 0.25 units backwards.

It is recommended to use the `[]` syntax to load the arguments for this step.

**Changelog**
* 1.2 - now is controlled by arguments (`[]` partially restores old behavior)
* 1.1 - initial implementation

**Examples**
* `transform[]`
* `transform:10`
* `transform::0,0,180`

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

**Changelog**
* 1.1 - initial implementation

**Examples**
* `collide`
* `collide:keep,descend:tube`
* `collide:descend:polyset:optimized_geom`
* `collide[]`

### Downscale

This step is used to resize one texture or all PNG textures in the folder
to a given size. Installing `Pillow` is required for this step (provided
by the `imagery` extra).

This step accepts up to four arguments.
* The first argument `size` is required. The desired texture size, which has
  to be a power-of-two. All affected textures will be resized to `size*size`.
* The second parameter `bbox` is optional. If it is not present, the textures
  will be resized as-is. If it is present, all textures will be first cropped
  to their bounding box before resizing, with `bbox%` padding around the
  bounding box. For example, setting `bbox=10` will use 10/12th of each
  dimension for the source image, and 1/12th of each dimension on each side
  for the padding.
* The third parameter `flags` is optional. It includes zero or more words
  separated by commas, defaults to no flags:
  * `truecenter`: By default, textures with big width and small height will be
    pinned to the bottom of the image. Setting this flag will instead center
    those textures in the image. This flag does not affect the textures with
    small width and big height, which will always be centered.
* The fourth argument `name` is optional, and defaults to
  an empty string. If name is empty, all textures will be resized, if name is 
  not empty, only the texture matching the given name will be resized. 
  This accepts Unix-style patterns (i.e. `background-*.png`).

**Changelog**
* 1.2.1 - initial implementation

**Examples**
* `downscale:256`
* `downscale:256:10`
* `downscale:256::truecenter:background-*.png`
* `downscale[]`

### Texture Cards

This step is used to create an EGG model out of a set of png/jpg files.
It is usually used to combine multiple related 2D images/icons together.
It is recommended to do `downscale` before this step, and `palettize` after
this step, but not required.

By default, all parts of the model will occupy the 1x1 unit square when loaded
in Panda3D. This is usually desired for assets such as icons, but not desired
for assets with variable sizes or non-uniform aspect ratio, such as GUI 
elements. In those cases, texture-cards can accept an argument for the size
of each model, which should be an integer (usually power-of-two). For example,
if this argument is set to `512`, 256x256 textures will have the Panda3D
size 0.5x0.5, and 128x1024 textures will have the size 0.25x2.

**Changelog**
* 1.2.1 - initial implementation

**Examples**
* `texture_cards`
* `texture_cards:512`

### Palettize

This step is used to join multiple texture files on a model into one palette.
It will palettize every EGG model in the folder.

This step takes up to two parameters. The first parameter is required: the
desired texture size. It must be a power of two. The default value is 1024,
which means each produced palette will be 1024x1024.

The second parameter is optional and includes zero or more comma-separated
words, defaults to empty:
* `ordered` - if the palettized images were named `{number}-{name}`, changes
  the palettized node name to `name`. Primarily used with texture-cards stage.

**Changelog**
* 1.2.1 - renamed from `3d_palettize` to `palettize`, added `ordered` flag
* 1.2 - initial implementation

**Examples**
* `palettize`
* `palettize:2048`

### Egg2Bam

This step is used to assemble the EGG model into the BAM model suitable
for ingame use. It also replaces the texture paths in the model, and 
copies the model and every needed texture into the `built` folder.
It takes no arguments.

**Changelog**
* 1.2 - now also patches the texture paths (before, this was done by optimize)
* 1.1 - initial implementation

**Examples**
* `egg2bam`

### Script

This step can be used to run scripts that are not packaged with this project.
The script will run in the directory including (transformed versions of) all
assets in the input directory. It will receive the name of the model as its only
argument. This step includes one parameter with the path to the script. Note that
due to the specifics of implementation, it has to be one file, but the type
of the script is not limited (shell, python, etc.) as long as it's an executable.

**Changelog**
* 1.1 - initial implementation

**Examples**
* `script:scripts/magic.sh`

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
* Addition of toon head functionality into the Asset Pipeline
