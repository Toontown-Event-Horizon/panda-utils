import shutil
import pathlib
import os

try:
    from PIL import Image
except ImportError:
    Image = None

from panda_utils.util import Context


def downscale(
    ctx: Context,
    path: str,
    scale: int,
    force: bool = False,
    bbox: int = -1,
    truecenter: bool = True,
    ignore_current_scale: bool = False,
) -> None:
    if Image is None:
        print("Install PIL to use downscaler: pip install -r requirements.txt")
        return

    original_path = f"{ctx.working_path}/{path}"
    backup_path = f"{ctx.working_path}/backup/{path}-{scale}"
    backup_obj = pathlib.Path(backup_path)
    backup_obj.mkdir(exist_ok=True, parents=True)

    files = os.listdir(original_path)
    for x in files:
        if ".png" in x:
            img = Image.open(f"{original_path}/{x}")
            if not ignore_current_scale and img.width == scale and img.height == scale:
                print(f"Skipping {x} as it is already resized")
                continue

            if not os.path.exists(f"{backup_path}/{x}"):
                shutil.copy(f"{original_path}/{x}", f"{backup_path}/{x}")
            else:
                name, ext = x.rsplit(".", 1)
                index = 1
                while os.path.exists(f"{backup_path}/{name}-{index}.{ext}"):
                    index += 1
                shutil.copy(f"{original_path}/{x}", f"{backup_path}/{name}-{index}.{ext}")

            if bbox >= 0:
                left, top, right, bottom = img.getbbox()
                bbox_w, bbox_h = (right - left) * bbox // 100, (bottom - top) * bbox // 100
                needed_width = right - left + bbox_w
                needed_height = bottom - top + bbox_h
                needed_size = max(needed_width, needed_height) * 2
                canvas = Image.new("RGBA", (needed_size, needed_size), (0, 0, 0, 0))
                canvas.paste(img.crop((left, top, right, bottom)), (bbox_w, bbox_h))
                img = canvas.crop((0, 0, right - left + 2 * bbox_w, bottom - top + 2 * bbox_h))

            if img.width != img.height:
                if not force and bbox == -1:
                    print(f"Skipping {x} due to invalid size: width {img.width}, height {img.height}")
                    continue

                # if we are asked to force downscale, try to add space, and center the image horizontally
                # but push it to the bottom vertically
                print("Force mode active, trying to add space...")
                if img.width > img.height and not truecenter:
                    img2 = Image.new("RGBA", (img.width, img.width))
                    img2.paste(img, (0, img.width - img.height, img.width, img.width))
                else:
                    # pixel-perfect operations moment
                    height_delta = (img.height + img.width) % 2
                    fh, fw = max(img.height, img.width), min(img.height, img.width)
                    even_fheight = fh + height_delta
                    img2 = Image.new("RGBA", (even_fheight, even_fheight))
                    x_coord = (even_fheight - fw) // 2
                    if fh == img.height:
                        img2.paste(img, (x_coord, height_delta, even_fheight - x_coord, even_fheight))
                    else:
                        img2.paste(img, (height_delta, x_coord, even_fheight, even_fheight - x_coord))
                img = img2

            print(f"Rescaling {x}")
            img.resize((scale, scale)).save(f"{original_path}/{x}")
