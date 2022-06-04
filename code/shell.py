import os
import shutil
import subprocess
from cmd import Cmd
from typing import List

from code import util
from code.tools import convert, palettize


class PandaShell(Cmd, util.Context):
    intro = 'Welcome to Panda Shell v0.1.'
    working_path = ''

    def __init__(self) -> None:
        Cmd.__init__(self)
        util.Context.__init__(self)
        self.do_cd(os.getcwd())

    def do_cd(self, path) -> None:
        if path == self.working_path:
            return

        self.working_path = path
        os.chdir(path)
        self.update_prompt()

    def update_prompt(self) -> None:
        self.prompt = f'p3d {self.working_path}> '

    def do_find(self, template) -> None:
        """Find files in the working directory or another directory."""
        subprocess.run(['find', *template.split()])

    def do_bam2egg(self, path) -> None:
        """Unpack a .bam file, bypassing texture requirements."""
        convert.bam2egg(self, path)

    def get_file_list(self, base_path, pattern) -> List[str]:
        path = f'{self.resources_path}/{base_path}'
        file_list = os.listdir(path)
        files = set(file_list)
        if pattern != '*':
            files_list = pattern.split()
        else:
            files_list = file_list
        return [x for x in files_list if x in files]

    def do_clean_palettize(self, arg) -> None:
        """Wipe a given phase directory."""
        shutil.rmtree(f'phase_{arg}', ignore_errors=True)
        shutil.rmtree(f'textures.txa', ignore_errors=True)
        shutil.rmtree(f'textures.boo', ignore_errors=True)

    def do_palettize(self, arg) -> None:
        """Accepts {name}, {phase}, {directory}. Palettizes phase_{phase}/maps/{directory} and saves a model
        into phase_{phase}/models/{directory}."""
        args = arg.split()
        if len(args) < 3:
            print('Invalid arguments. Expected {name} {phase_number} {subdirectory}.')
            return
        palettize.palettize(self, *args)
