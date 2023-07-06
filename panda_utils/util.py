import importlib.resources
import logging
import os
import pathlib
import subprocess
import re
import sys
from typing import List

logger = logging.getLogger("panda_utils.palettize")


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
        paths = cfg.get("paths", {})
        obj.resources_path = paths.get("resources")
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
            ]
            for path in paths:
                if path:
                    obj.panda_path = str(path.parent)
                    break
        if not obj.panda_path:
            obj.panda_path = paths.get("panda")
        if not obj.panda_path:
            raise ValueError("Panda3D was not found on the search path!")
        return obj


def get_file_list(init_path: str, base_path: str) -> List[str]:
    path = f"{init_path}/{base_path}"
    if not os.path.exists(path):
        return []

    return [file for file in os.listdir(path) if os.path.isfile(f"{path}/{file}")]


def run_panda(ctx: Context, command: str, *args: str, timeout: int = 10, debug: bool = False) -> str:
    process = subprocess.Popen(
        [f"{ctx.panda_path}/{command}", *args], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
    )
    out = process.communicate(timeout=timeout)
    bts = out[1] if isinstance(out, tuple) else out
    out_str = bts.decode("utf-8")
    if process.returncode or debug:
        logger.warning(out_str)
    return out_str


def get_data_file_path(filename):
    return importlib.resources.files("panda_utils").joinpath(filename)


interactive = False
toon_head_phase = "phase_3"
