import os
import pathlib
import shutil

from code import util


def bam2egg(ctx: util.Context, path: str) -> None:
    output = util.run_panda(ctx, 'bam2egg', path, '-o', path.replace('bam', 'egg'))
    errored_files = ctx.regex_collection.not_found.findall(output)
    if not errored_files:
        print('Recompilation not needed!')
        return

    for x in errored_files:
        if not os.path.exists(f'{ctx.resources_path}/{x}'):
            p2 = input(f'Unable to find {x} in resources. Enter path to copy from: ')
            if not p2:
                print(f'Unable to get {x} from anywhere, aborting.')
                return
        else:
            p2 = f'{ctx.resources_path}/{x}'
        print(f'Copying {x} from resources.')
        pathlib.Path('/'.join(x.split('/')[:-1])).mkdir(exist_ok=True, parents=True)
        shutil.copy(p2, x)
    print('Recompiling egg...')
    util.run_panda(ctx, 'bam2egg', path, '-o', path.replace('bam', 'egg'))
