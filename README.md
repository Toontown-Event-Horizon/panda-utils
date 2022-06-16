# Panda3D Utils v0.1
 
This repository includes multiple tools for some basic Panda3D automation. Written in Python.

## Installation
* Clone this repository.
* Copy `config_example.ini` into `config.ini` and modify as needed.
* Run in directory of your choice. That directory will have temporary files, so
using the production directory is not recommended.

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
  * Run: `python main.py palettize <directory_name> <phase_num> <model_type> <pattern>`
    * The explanation below assumes your images are located in
    `resources/phase_6/maps/guns`.
    * `directory_name` is the directory containing the images, i.e. `guns`.
    * `phase_num` is `6` in this scenario, `model_type` is probably `props`.
    * The palette will be saved under `resources/phase_6/maps`,
    and the model under `resources/phase_6/model/props`. The initial images can be
    safely removed after running.
    * `pattern` is optional and defaults to `*`. Right now it can either be `*` or the
    list of file names (i.e. `"water_gun.png fire_thrower.png laser.png"`). Self-explanatory.
  * Can use files from under working directory as well as the resource
  directory. Uses the working directory by default, delete or rename files
  to load the original ones.
* Automatic downscaler
  * Many times, assets are made in high resolution, and then have to be downscaled to
  a smaller one - 512x512 or 256x256.
  * Doing this by hand is a tedious process. This script can do it automatically.
  * By default, only perfectly square images are processed. `--force` can be used to
  process rectangular images with a small accuracy loss.
  * Run: `python main.py downscale <directory_path> <128|256|512|1024|2048>`

### Coming soon
* Reverse palettizing based on the image coordinates