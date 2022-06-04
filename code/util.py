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
    def from_config(cls, cfg: dict) -> 'Context':
        obj = cls()
        obj.working_path = os.getcwd()
        obj.resources_path = cfg['paths']['resources']
        obj.panda_path = cfg['paths']['panda']
        return obj


def get_file_list(ctx: Context, base_path: str, pattern: str) -> List[str]:
    path = f'{ctx.resources_path}/{base_path}'
    file_list = os.listdir(path)
    files = set(file_list)
    if pattern != '*':
        files_list = pattern.split()
    else:
        files_list = file_list
    return [x for x in files_list if x in files]


def run_panda(ctx: Context, command: str, *args: str, timeout: int = 2, debug: bool = False) -> str:
    out = subprocess.Popen([f'{ctx.panda_path}/{command}', *args], stdout=subprocess.DEVNULL,
                           stderr=subprocess.PIPE).communicate(timeout=timeout)
    bts = out[1] if isinstance(out, tuple) else out
    out_str = bts.decode('utf-8')
    if debug:
        print(out_str)
    return out_str
