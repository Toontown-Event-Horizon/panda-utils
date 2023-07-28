from panda_utils.eggtree import eggparse


def set_texture_prefix(tree: eggparse.EggTree, new_prefix: str) -> None:
    textures = tree.findall("Texture")
    for texture in textures:
        texture_name = texture.get_child(0)
        og_filename = eggparse.sanitize_string(texture_name.value)
        if og_filename.startswith(new_prefix) and "/.." not in og_filename:
            continue
        filename = og_filename.split("/")[-1]
        texture_name.value = f"{new_prefix}/{filename}"


def add_comment(tree: eggparse.EggTree, comment: str) -> None:
    comment_str = eggparse.EggString(f'"{comment}"')
    comment_tree = eggparse.EggTree(comment_str)
    comment = eggparse.EggBranch("Comment", None, comment_tree)
    tree.children.insert(1, comment)
