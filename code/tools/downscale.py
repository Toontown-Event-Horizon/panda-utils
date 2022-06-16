import shutil
import pathlib
import os

try:
    from PIL import Image
except ImportError:
    Image = None

from code.util import Context


def downscale(ctx: Context, path: str, scale: int, force: bool = False) -> None:
    if Image is None:
        print('Install PIL to use downscaler: pip install -r requirements.txt')
        return

    original_path = f'{ctx.working_path}/{path}'
    backup_path = f'{ctx.working_path}/backup/{path}-{scale}'
    backup_obj = pathlib.Path(backup_path)
    backup_obj.mkdir(exist_ok=True, parents=True)

    files = os.listdir(original_path)
    for x in files:
        if '.png' in x:
            img = Image.open(f'{original_path}/{x}')
            if img.width == scale and img.height == scale:
                print(f'Skipping {x} as it is already resized')
                continue
            shutil.copy(f'{original_path}/{x}', f'{backup_path}/{x}')

            if img.width != img.height:
                if not force:
                    print(f'Skipping {x} due to invalid size: width {img.width}, height {img.height}')
                    continue

                # if we are asked to force downscale, try to add space, and center the image horizontally
                # but push it to the bottom vertically
                print('Force mode active, trying to add space...')
                if img.width > img.height:
                    img2 = Image.new('RGBA', (img.width, img.width))
                    img2.paste(img, (0, img.width - img.height, img.width, img.width))
                else:
                    # pixel-perfect operations moment
                    height_delta = abs(img.height - img.width) % 2
                    even_height = img.height + height_delta
                    img2 = Image.new('RGBA', (even_height, even_height))
                    x_coord = (even_height - img.width) // 2
                    img2.paste(img, (x_coord, height_delta, even_height - x_coord, even_height))
                img = img2

            print(f'Rescaling {x}')
            img.resize((scale, scale)).save(f'{original_path}/{x}')
