from panda_utils.eggtree import eggparse


def set_texture_prefix(tree: eggparse.EggTree, new_prefix: str) -> None:
    textures = tree.findall("Texture")
    for texture in textures:
        texture_name = texture.get_child(0)
        # This thing is a bit annoying because right now eggtree does not remove the quotes from strings
        # So if there's no quotes, both quotes will remain in the filename, causing quote duplication
        filename = texture_name.value[1:].split("/")[-1]
        texture_name.value = f"{texture_name.value[0]}{new_prefix}/{filename}"


def add_comment(tree: eggparse.EggTree, comment: str) -> None:
    comment_str = eggparse.EggString(f'"{comment}"')
    comment_tree = eggparse.EggTree(comment_str)
    comment = eggparse.EggBranch("Comment", None, comment_tree)
    tree.children.insert(1, comment)
