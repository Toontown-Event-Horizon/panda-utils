import distutils.spawn
import importlib.resources
import logging
import os
import pathlib
import subprocess
import re
import sys
from enum import Enum
from typing import List

logger = logging.getLogger("panda_utils.palettize")


class LoggingScope(Enum):
    PANDA3D = "panda"
    PIPELINE = "pipeline"
    BLENDER = "blender"


def get_debug(scope: LoggingScope):
    var_names = {
        LoggingScope.PANDA3D: "PANDA_UTILS_P3D_DEBUG",
        LoggingScope.PIPELINE: "PANDA_UTILS_LOGGING",
        LoggingScope.BLENDER: "PANDA_UTILS_BLENDER_LOGGING"
    }
    if os.getenv(var_names[scope]):
        return True

    flags = os.getenv("PANDA_UTILS_DEBUG", "").split(",")
    if scope in flags or "all" in flags:
        return True

    return False


class RegexCollection:
    def __init__(self):
        self.not_found = re.compile("couldn't read: ([^\n]+)")
        self.find_pat = re.compile(r"^\[(.+)]$")


class Context:
    working_path: str
    resources_path: str
    panda_path: str

    def __init__(self):
        self.regex_collection = RegexCollection()

    @classmethod
    def from_config(cls, cfg: dict) -> "Context":
        obj = cls()
        obj.working_path = os.getcwd()
        cfg_paths = cfg.get("paths", {})
        obj.resources_path = cfg_paths.get("resources")
        if not obj.resources_path:
            raise ValueError("The config requires setting paths.resources!")

        options = cfg.get("options", {})
        obj.panda_path = ""
        if options.get("panda3d_path_inherit"):
            python_path = os.path.dirname(sys.executable)
            paths = [
                pathlib.Path(python_path, "egg-trans"),
                pathlib.Path(python_path, "egg-trans.exe"),
                pathlib.Path(python_path, "bin", "egg-trans"),
                pathlib.Path(python_path, "bin", "egg-trans.exe"),
                pathlib.Path(python_path, "..", "bin", "egg-trans"),
                pathlib.Path(python_path, "..", "bin", "egg-trans.exe"),
            ]
            for path in paths:
                if path.exists():
                    obj.panda_path = str(path.parent)
                    break
        if not obj.panda_path:
            obj.panda_path = cfg_paths.get("panda")
        if not obj.panda_path:
            raise ValueError("Panda3D was not found on the search path!")
        return obj


def get_file_list(init_path: str, base_path: str) -> List[str]:
    path = f"{init_path}/{base_path}"
    if not os.path.exists(path):
        return []

    return [file for file in os.listdir(path) if os.path.isfile(f"{path}/{file}")]


def choose_binary(*filename):
    filename = os.path.sep.join(filename)
    path = pathlib.Path(filename)
    if path.is_absolute():
        if path.exists():
            return filename
        exe_filename = filename + ".exe"
        if pathlib.Path(exe_filename).exists():
            return exe_filename
        raise RuntimeError(f"Unable to find binary (installation issue): {filename}")
    elif path := distutils.spawn.find_executable(filename):
        return path
    elif path := distutils.spawn.find_executable(filename + ".exe"):
        return path
    else:
        raise RuntimeError(f"Unable to find binary (not on PATH): {filename}")


def run_panda(ctx: Context, command: str, *args: str, timeout: int = 10, debug: bool = False) -> str:
    process = subprocess.Popen(
        [choose_binary(ctx.panda_path, command), *args], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
    )
    out = process.communicate(timeout=timeout)
    bts = out[1] if isinstance(out, tuple) else out
    out_str = bts.decode("utf-8")
    if process.returncode or debug or get_debug(LoggingScope.PANDA3D):
        logger.warning(out_str)
    return out_str


def get_data_file_path(filename):
    return importlib.resources.files("panda_utils").joinpath(filename)


interactive = False
toon_head_phase = "phase_3"
