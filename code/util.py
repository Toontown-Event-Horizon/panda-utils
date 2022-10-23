import os
import subprocess
import re
from typing import List


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
        obj.resources_path = cfg["paths"]["resources"]
        obj.panda_path = cfg["paths"]["panda"]
        return obj


def get_file_list(init_path: str, base_path: str) -> List[str]:
    path = f"{init_path}/{base_path}"
    if not os.path.exists(path):
        return []

    return os.listdir(path)


def run_panda(ctx: Context, command: str, *args: str, timeout: int = 2, debug: bool = False) -> str:
    process = subprocess.Popen(
        [f"{ctx.panda_path}/{command}", *args], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
    )
    out = process.communicate(timeout=timeout)
    bts = out[1] if isinstance(out, tuple) else out
    out_str = bts.decode("utf-8")
    if process.returncode or debug:
        print(out_str)
    return out_str
