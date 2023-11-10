from panda_utils.eggtree.nodes import EggTree, EggLeaf


def sanitize_string(val):
    if val and val[0] in "\"'":
        return val[1:-1]
    return val


def set_texture_prefix(tree: EggTree, new_prefix: str, *, only_absolute: bool = False) -> None:
    textures = tree.findall("Texture")
    for texture in textures:
        texture_name = texture.get_child(0)
        og_filename = sanitize_string(texture_name.value)
        if og_filename.startswith(new_prefix) and "/.." not in og_filename:
            continue
        if only_absolute and not og_filename.startswith("/"):
            continue
        filename = og_filename.split("/")[-1]
        texture_name.value = f"{new_prefix}/{filename}"


def add_comment(tree: EggTree, comment: str) -> None:
    comment = EggLeaf("Comment", None, comment)
    tree.children.insert(1, comment)
