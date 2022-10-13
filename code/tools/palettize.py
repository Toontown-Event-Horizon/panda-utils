import os
import pathlib
import shutil

from code import util
from code.eggtree import eggparse


def palettize(ctx: util.Context, name: str, phase: str, subdir: str, poly: int = None, margin: int = 0,
              ordered: bool = False) -> None:
    map_path, model_path = f'phase_{phase}/maps', f'phase_{phase}/models/{subdir}'
    pathlib.Path(map_path).mkdir(exist_ok=True, parents=True)
    pathlib.Path(model_path).mkdir(exist_ok=True, parents=True)

    file_list = set(util.get_file_list(ctx.resources_path, f'{map_path}/{name}'))
    existing_file_list = set(util.get_file_list(ctx.working_path, f'{map_path}/{name}'))
    print(f'Found {len(file_list - existing_file_list)} files, copying to the workspace...')
    for x in file_list:
        if not os.path.exists(f'{ctx.working_path}/{map_path}/{name}/{x}'):
            shutil.copy(f'{ctx.resources_path}/{map_path}/{name}/{x}', f'{ctx.working_path}/{map_path}/{name}/{x}')
    print('Running egg-texture-cards...')
    egg_path = f'{model_path}/{name}.egg'
    union = file_list.union(existing_file_list)
    args = ['-o', egg_path]
    if poly:
        args += ['-p', f'{poly},{poly}']
    args += [f'{map_path}/{name}/{x}' for x in union]
    util.run_panda(ctx, 'egg-texture-cards', *args)

    print('Creating a TXA file...')
    # txa_text = self.create_txa(2048, file_list)
    txa_text = ":palette 2048 2048\n" \
               ":imagetype png\n" \
               ":powertwo 1\n" \
               f":group {name} dir phase_{phase}/maps\n" \
               f"*.png : force-rgba dual linear clamp_u clamp_v margin {margin}\n"
    with open('textures.txa', 'w') as txa_file:
        txa_file.write(txa_text)

    print('Palettizing...')
    util.run_panda(ctx, 'egg-palettize', '-opt', '-redo', '-noabs', '-nodb', '-inplace', egg_path, '-dm', map_path,
                   '-tn', f'mk2_{name}_palette_%p_%i', timeout=60)
    print('Transforming eggs...')
    util.run_panda(ctx, 'egg-trans', egg_path, '-pc', map_path, '-o', egg_path)

    if ordered:
        print('Removing ordering indices from the egg...')
        with open(egg_path) as f:
            data = f.readlines()

        eggtree = eggparse.egg_tokenize(data)
        all_groups = eggtree.findall("Group")
        for group in all_groups:
            if "-" not in group.node_name:
                continue

            name_split = group.node_name.split('-', 1)
            try:
                int(name_split[0])
            except ValueError:
                continue
            else:
                group.node_name = name_split[1]

        with open(egg_path, 'w') as f:
            f.write(str(eggtree))

    print('Converting to BAM...')
    util.run_panda(ctx, 'egg2bam', egg_path, '-o', egg_path.replace('.egg', '.bam'), timeout=10)
    print('Cleaning up...')
    shutil.rmtree(f'{model_path}/phase_{phase}', ignore_errors=True)  # happens due to a bug
    # os.unlink(egg_path)
    os.unlink('textures.txa')
    print('Palettizing complete.')
