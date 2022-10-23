import shutil
import pathlib
import os

try:
    from PIL import Image
except ImportError:
    Image = None

from code.util import Context


def downscale(ctx: Context, path: str, scale: int, force: bool = False, bbox: int = -1,
              truecenter: bool = True) -> None:
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

            if bbox >= 0:
                left, top, right, bottom = img.getbbox()
                bbox_w, bbox_h = (right - left) * bbox // 100, (bottom - top) * bbox // 100
                left = max(0, left - bbox_w)
                top = max(0, top - bbox_h)
                right = min(img.width, right + bbox_w)
                bottom = min(img.height, bottom + bbox_h)
                img = img.crop((left, top, right, bottom))

            if img.width != img.height:
                if not force and bbox == -1:
                    print(f'Skipping {x} due to invalid size: width {img.width}, height {img.height}')
                    continue

                # if we are asked to force downscale, try to add space, and center the image horizontally
                # but push it to the bottom vertically
                print('Force mode active, trying to add space...')
                if img.width > img.height and not truecenter:
                    img2 = Image.new('RGBA', (img.width, img.width))
                    img2.paste(img, (0, img.width - img.height, img.width, img.width))
                else:
                    # pixel-perfect operations moment
                    height_delta = (img.height + img.width) % 2
                    fh, fw = max(img.height, img.width), min(img.height, img.width)
                    even_fheight = fh + height_delta
                    img2 = Image.new('RGBA', (even_fheight, even_fheight))
                    x_coord = (even_fheight - fw) // 2
                    if fh == img.height:
                        img2.paste(img, (x_coord, height_delta, even_fheight - x_coord, even_fheight))
                    else:
                        img2.paste(img, (height_delta, x_coord, even_fheight, even_fheight - x_coord))
                img = img2

            print(f'Rescaling {x}')
            img.resize((scale, scale)).save(f'{original_path}/{x}')
