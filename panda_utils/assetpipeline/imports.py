from .models import *  # noqa: F401
from .misc import *  # noqa: F401
from .textures import *  # noqa: F401
from .blender import *  # noqa: F401

ALL_ACTIONS = {
    "_".join(action.split("_")[1:]): callback for action, callback in globals().items() if action.startswith("action_")
}
