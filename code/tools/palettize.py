import os
import pathlib
import shutil

from code import util


def palettize(ctx: util.Context, name: str, phase: str, subdir: str, pattern1: str = '*', *pattern_extra: str) -> None:
    patt = [pattern1, *pattern_extra]
    map_path, model_path = f'phase_{phase}/maps', f'phase_{phase}/models/{subdir}'
    pathlib.Path(map_path).mkdir(exist_ok=True, parents=True)
    pathlib.Path(model_path).mkdir(exist_ok=True, parents=True)

    file_list = util.get_file_list(ctx, f'{map_path}/{name}', ' '.join(patt))
    print(f'Found {len(file_list)} files, copying to the workspace...')
    for x in file_list:
        shutil.copy(f'{ctx.resources_path}/{map_path}/{name}/{x}', f'{ctx.working_path}/{map_path}/{x}')
    print('Running egg-texture-cards...')
    egg_path = f'{model_path}/{name}.egg'
    util.run_panda(ctx, 'egg-texture-cards', '-o', egg_path, *[f'{map_path}/{x}' for x in file_list])

    print('Creating a TXA file...')
    # txa_text = self.create_txa(2048, file_list)
    txa_text = ":palette 2048 2048\n" \
               ":imagetype png\n" \
               ":powertwo 1\n" \
               f":group {name} dir phase_{phase}/maps\n" \
               "*.png : force-rgba dual linear clamp_u clamp_v margin 0\b"
    with open('textures.txa', 'w') as txa_file:
        txa_file.write(txa_text)

    print('Palettizing...')
    util.run_panda(ctx, 'egg-palettize', '-opt', '-redo', '-noabs', '-nodb', '-inplace', egg_path, '-dm', map_path,
                   '-tn', f'mk2_{name}_palette_%p_%i', timeout=60)
    print('Transforming eggs...')
    util.run_panda(ctx, 'egg-trans', egg_path, '-pc', map_path, '-o', egg_path)
    print('Converting to BAM...')
    util.run_panda(ctx, 'egg2bam', egg_path, '-o', egg_path.replace('.egg', '.bam'))
    print('Cleaning up...')
    shutil.rmtree(f'{model_path}/phase_{phase}')
    for x in file_list:
        os.unlink(f'{ctx.working_path}/{map_path}/{x}')
    os.unlink(egg_path)
    os.unlink('textures.txa')
    print('Palettizing complete.')
