# Panda3D Utils v1.5
 
Panda Utils is a set of Python scripts meant to help various projects
running on the game engine [Panda3D](https://panda3d.org).
It includes tools for manual use, as well as a full-fledged asset
importing pipeline. It also includes an implementation of Egg Syntax Tree,
which can be used programmatically in some scenarios.

## Installation
* Install Python 3.9 or above
* `pip install panda_utils`
* This package includes a number of optional dependencies:
  * `pip install panda_utils[imagery]` to enable the Downscale module
  * `pip install panda_utils[autopath]` to automatically download P3D
  * `pip install panda_utils[runnable]` to enable the CLI runner
    * Requires a settings file to be used that way, see: `config_example.ini`
      in this repository
  * `pip install panda_utils[pipeline]` to enable the Pipeline runner
    * Requires Blender to be in the system PATH to run
  * `pip install panda_utils[composer]` to use the Composer tool
    used for Pipeline automation
    * Requires `pipeline` and has the same requirements for Blender
  * `pip install panda_utils[everything]` to include all of the above

## Some of the features
* Automated asset pipeline, allowing to build BAM model files from input
  FBX or BLEND models adding optimizations and modifying them on the fly
* A tool to easily rescale and palettize all images in a folder
* Bam2Egg converter that does not suck
* A tool to export toon model and fix most issues arising from that
* Fast and flexible implementation of the Egg Syntax Tree

## Documentation

See here: [Documentation](https://panda-utils.readthedocs.io/en/latest/)
