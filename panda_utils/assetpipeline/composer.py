import os
import pathlib
import shutil
import sys

import doit
import yaml

from panda_utils.assetpipeline.commons import BUILT_FOLDER, INPUT_FOLDER, file_out_regex, YAML_CONFIG_FILENAME
from panda_utils.assetpipeline.target_parser import StepContext, TargetsFile, make_pipeline

PANDA_UTILS = f"{sys.executable} -m panda_utils.assetpipeline"
DOIT_CONFIG = {"default_tasks": ["build"]}
ALL_FILES = []
COMMON_TS = []


def resolve_cwd(filename):
    current_folder = pathlib.Path(os.getcwd())
    attempts = 0
    while attempts < 25 and not (current_folder / filename).exists():
        attempts += 1
        current_folder = current_folder.parent

    if not (current_folder / filename).exists():
        print(f"Error: Unable to locate {filename}. Make sure this file exists and try again.")
        exit(1)

    os.chdir(current_folder)


def load_from_file(filename, asset_markers=()):
    with open(filename) as f:
        tf = TargetsFile(**yaml.safe_load(f))

    COMMON_TS.extend(tf.common.items())

    for folder in os.listdir(INPUT_FOLDER):
        if folder not in tf.targets:
            raise ValueError(
                f"Unknown folder: {folder}! If you are not intending to build it, add it with active=False."
            )

        tgt = tf.targets[folder]
        if not tgt.active:
            continue

        subtasks = []
        for dirname, dirs, files in os.walk(INPUT_FOLDER / folder):
            if not dirs:
                subtasks.append(pathlib.Path(dirname))
            elif any(marker for marker in files if marker in asset_markers):
                subtasks.append(pathlib.Path(dirname))
                dirs[:] = []

        for task in subtasks:
            ctx = StepContext(os.listdir(task), tf.settings, tgt.import_method or tf.settings.default_import_method)
            pipeline = make_pipeline(tgt, task.name, ctx)
            if pipeline is None:
                continue

            if tgt.copy_subdir != 0:
                # We set up so if we are negative we work up from our file
                # If we are positive we work down from input
                end = 0 if tgt.copy_subdir < 0 else tgt.copy_subdir + 2
                start = tgt.copy_subdir if tgt.copy_subdir < 0 else 2
            
                if max(abs(end), abs(start)) > len(task.parts):
                    raise ValueError(
                        f"Copy_subdir value for: {folder} is greater then the dir depth found. Use a smaller number."
                    )

                model_path = tgt.model_path
                texture_path = tgt.texture_path

                for i in range(start, end, 1):
                    model_path += f"/{task.parts[i]}"
                    texture_path += f"/{task.parts[i]}"
            else:
                model_path = tgt.model_path
                texture_path = tgt.texture_path

            pipeline = f"{PANDA_UTILS} {task} {model_path} {texture_path} {pipeline}"
            requires_commons = " cts" in pipeline
            target_model = BUILT_FOLDER / model_path / f"{task.name}.bam"

            rm_files = []
            path = BUILT_FOLDER / texture_path
            if path.exists():
                for file in os.listdir(path):
                    if file.startswith(task.name) and file_out_regex.match(file):
                        rm_files.append(path / file)
            ALL_FILES.append((task, pipeline.split(), target_model, requires_commons, rm_files))


def task_copy():
    """
    Copies the files from the built/ directory into the project directory.
    """

    def copy_files():
        from panda_utils.__main__ import make_context
        panda_utils_ctx = make_context()
        target_path = panda_utils_ctx.resources_path
        for phase in os.listdir(BUILT_FOLDER):
            shutil.copytree(pathlib.Path(BUILT_FOLDER, phase), target_path, dirs_exist_ok=True)

    return {
        "actions": [copy_files],
    }


def check_target(task, values, callback):
    def save_callback():
        return {"callback": callback}

    task.value_savers.append(save_callback)
    return values.get("callback") == callback


def task_copy_commons():
    """
    Copies all commonly used textures.
    """

    def copy_files():
        for from_name, to_name in COMMON_TS:
            from_path = pathlib.Path("common", from_name)
            to_path = pathlib.Path(BUILT_FOLDER, pathlib.PurePosixPath(to_name))
            shutil.rmtree(to_path, ignore_errors=True)
            shutil.copytree(from_path, to_path)

    return {
        "actions": [copy_files],
    }


def task_build():
    """
    Builds a model or all models. Only does so if something in the build process of the model changed.
    """

    def rm_files(files: list[pathlib.Path]):
        for file in files:
            file.unlink()

    for folder, callback, target_model, requires_commons, tex_files in ALL_FILES:
        yield {
            "name": folder.name,
            "actions": [(rm_files, [tex_files]), callback],
            "file_dep": [pathlib.Path(dirname) / file for dirname, dirs, files in os.walk(folder) for file in files],
            "targets": [target_model],
            "verbosity": 2,
            "uptodate": [(check_target, [callback])],
            "clean": True,
            "task_dep": ["copy_commons"] if requires_commons else [],
        }


def task_rebuild():
    """
    Builds a model or all models. Ignores dependencies, which means it will rebuild the model even if nothing changed.
    """
    for value in task_build():
        value.pop("file_dep", None)
        value.pop("targets", None)
        value.pop("clean", None)
        value["uptodate"] = [False]  # noqa
        yield value


def main():
    resolve_cwd("targets.yml")
    load_from_file("targets.yml", {YAML_CONFIG_FILENAME})
    doit.run(globals())


if __name__ == "__main__":
    main()
