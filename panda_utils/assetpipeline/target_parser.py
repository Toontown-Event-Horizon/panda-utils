import abc
import dataclasses
import os
from enum import Enum
from typing import Union

from pydantic import BaseModel

from panda_utils.assetpipeline.commons import command_regex, preblend_regex, regex_mcf, regex_mcf_fallback

IS_PRODUCTION = bool(os.getenv("PANDA_UTILS_PRODUCTION"))
Parameter = Union[None, str, dict, list, bool]
"""
String parameters get passed to the pipeline as is.
None parameters run the step with zero parameters.
Dict parameters use {} notation, regardless of dict content.
List parameters use [] notation, if the list is empty.
List parameters make multiple calls, if the list is not empty. It may include other lists
or dictionaries, but all of them will be considered empty.
False parameters will not run the action at all.
True parameters mean the parameter was not passed and the default one should be used.
"""


def stringify_param(x: Parameter):
    if x is None:
        return ""
    if isinstance(x, str):
        return ":" + x
    if isinstance(x, dict):
        return "{}"
    if isinstance(x, list):
        return "[]"
    raise ValueError(f"Invalid parameter: {x}")


class ImportMethod(Enum):
    GLTF2BAM = "gltf2bam"
    """Export using gltf2bam utility. This invokes the blend2bam step of pipeline."""

    BLEND2BAM = "blend2bam"
    """
    Export using blend2bam utility. This invokes the blend2bam step of pipeline.
    NOTE: this is not supported on Windows, use gltf2bam instead, it's mostly the same.
    """

    YABEE = "yabee"
    """Export using YABEE utility. Requires the use of our fork."""


class CollisionSystem(Enum):
    BUILTIN = "builtin"
    BULLET = "bullet"


class CallbackType(Enum):
    STANDARD = "standard"
    """Exports a model normally. Available exporters: gltf2bam, blend2bam, yabee."""

    ACTOR = "actor"
    """
    Exports an actor and all of the actions specified in the config file.
    If no actions are specified, exports no actions.
    Available exporters: yabee. Will force change the exporter of this model to yabee if used.
    """

    TWO_D_PALETTE = "2d-palette"
    """Makes a 2D palette out of all images in the folder. Available exporters: not applicable."""


class TFSettings(BaseModel):
    default_import_method: ImportMethod = ImportMethod.GLTF2BAM
    """
    Models will be exported into EGG files using this pipeline by default.
    Can be overridden on model level or on folder level as well.
    """

    collision_system: CollisionSystem = CollisionSystem.BUILTIN
    """
    Only has effect when using gltf2bam or blend2bam. YABEE always exports with builtin collisions.
    It is usually easier to use the collide settings instead of this.
    """

    srgb_textures: bool = False
    """True if you use srgb textures. Only has effect with blend2bam or gltf2bam."""

    legacy_materials: bool = False
    """True if you export materials for old versions of Panda3D."""


class ExtraStep(BaseModel):
    after: str = ""
    """
    Force a step to be AFTER a certain step. At least 1 of after and before is required.
    Pipeline assumes most steps commute, so if two steps have the same AFTER value
    the order in which they appear will not be guaranteed.
    """

    before: str = ""
    """
    Force a step to be BEFORE a certain step. At least 1 of after and before is required.
    Pipeline assumes most steps commute, so if two steps have the same BEFORE value
    the order in which they appear will not be guaranteed.
    """

    parameters: Parameter = None

    production: bool = None
    """
    Steps that have this at false will only run in dev, steps that have this at true will only run in prod.
    """


class TargetOverride(BaseModel):
    extra_steps: dict[str, Union[ExtraStep, list[ExtraStep]]] = None
    parameters: dict[str, Parameter] = None
    callback_type: CallbackType = None
    active: bool = None
    import_method: ImportMethod = None


class SingleTarget(BaseModel):
    model_config = {"protected_namespaces": ()}

    active: bool = True
    """False if this model should not be built."""

    model_path: str
    """Where to put the model after exporting? For example: phase_3/models/gui. Required."""

    texture_path: str
    """Where to put the texture after exporting? For example: phase_3/maps. Required."""

    callback_type: CallbackType = CallbackType.STANDARD
    """Callback type. Currently supported: standard, actor, 2d palette."""

    parameters: dict[str, Parameter] = {}
    """Overrides the default parameters on certain operations."""

    extra_steps: dict[str, Union[ExtraStep, list[ExtraStep]]] = {}
    """
    Extra steps that have to be performed in the pipeline.
    Key is the step name, value includes the parameters.
    Use list if you need the same step multiple times.
    """

    overrides: dict[str, TargetOverride] = {}
    """
    Includes target definitions when they're different.
    Any field that was not overridden remains the same.
    """

    import_method: ImportMethod = None
    """Allows overriding the default_import_method set in settings."""


class TargetsFile(BaseModel):
    """The definition of targets.yml file as read by the Composer module."""

    common: dict[str, str] = {}
    """
    Folders that are available for common texture set operation.
    Key = name of the folder inside common/, value = path to the folder where the set should be copied.
    """

    settings: TFSettings = TFSettings()
    """Default settings for the composer."""

    targets: dict[str, SingleTarget]
    """The configuration for each folder in the input folder. Required."""


@dataclasses.dataclass
class StepContext:
    files: list[str]
    settings: TFSettings
    exporter: ImportMethod
    exporter_override: Union[ImportMethod, None] = None
    parameter: Parameter = None


class Step(abc.ABC):
    name: str

    @abc.abstractmethod
    def make_string(self, ctx: StepContext) -> str:
        pass


class ConstantStep(Step):
    def __init__(self, value):
        self.value = value
        if regex_mcf.match(value) or regex_mcf_fallback.match(value):
            self.name = value[:-2]
        else:
            self.name = value

    def make_string(self, ctx: StepContext):
        return self.value


class ParametrizedStep(Step):
    def __init__(self, name, default: Parameter = False):
        self.name = name
        self.default = default

    def make_string(self, ctx: StepContext):
        param = self.default if ctx.parameter is True else ctx.parameter
        if param is False:
            return ""
        return self.name + stringify_param(param)


class Preexport(Step):
    name = "preexport"

    def make_string(self, ctx: StepContext):
        if ctx.parameter is False:
            return ""
        if any(preblend_regex.match(f) for f in ctx.files):
            return "preblend"
        return "blendrename"


class Export(Step):
    name = "blend2bam"

    def make_string(self, ctx: StepContext):
        exporter = ctx.exporter_override or ctx.exporter
        if exporter == ImportMethod.YABEE:
            return "yabee{}"
        else:
            cmd = "blend2bam"
            flags = []
            if exporter == ImportMethod.BLEND2BAM:
                flags.append("b2b")
            if ctx.settings.srgb_textures:
                flags.append("srgb")
            if ctx.settings.collision_system == CollisionSystem.BULLET:
                flags.append("bullet")
            if ctx.settings.legacy_materials:
                flags.append("legacy")
            return cmd + ":" + ",".join(flags) + " bam2egg"


@dataclasses.dataclass
class PipelineBlockout:
    steps: list[Step]
    exporters: list[ImportMethod]


PIPELINE_BLOCKOUTS = {
    CallbackType.STANDARD: PipelineBlockout(
        exporters=[ImportMethod.GLTF2BAM, ImportMethod.BLEND2BAM, ImportMethod.YABEE],
        steps=[
            ParametrizedStep("downscale"),
            ParametrizedStep("cts"),
            Preexport(),
            Export(),
            ConstantStep("collide[]"),
            ConstantStep("transform[]"),
            ConstantStep("group_rename[]"),
            ConstantStep("group_remove[]"),
            ParametrizedStep("palettize"),
            ParametrizedStep("optimize", default=None),
            ConstantStep("uvscroll[]"),
            ParametrizedStep("egg2bam", default=None),
        ],
    ),
    CallbackType.ACTOR: PipelineBlockout(
        exporters=[ImportMethod.YABEE],
        steps=[
            ParametrizedStep("downscale"),
            ParametrizedStep("cts"),
            Preexport(),
            Export(),  # always uses YABEE
            ConstantStep("collide[]"),
            ConstantStep("transform[]"),
            ConstantStep("group_rename[]"),
            ConstantStep("group_remove[]"),
            ParametrizedStep("palettize"),
            ParametrizedStep("optimize", default=None),
            ParametrizedStep("optchar", default=[]),
            ConstantStep("uvscroll[]"),
            ParametrizedStep("egg2bam", default=None),
        ],
    ),
    CallbackType.TWO_D_PALETTE: PipelineBlockout(
        exporters=[],
        steps=[
            ParametrizedStep("downscale"),
            ParametrizedStep("texture_cards", default=None),
            ParametrizedStep("palettize", default="1024"),
            ParametrizedStep("egg2bam", default=None),
        ],
    )
}


def step_matches(step: str, find: str):
    if not find:
        return False
    if command_regex.match(find) and step.startswith(find):
        return True
    return find == step


def insert_extra_step(pipeline: list[str], name: str, item: ExtraStep):
    if item.production is not None and item.production != IS_PRODUCTION:
        return

    insert_step = -1
    for index, step in enumerate(pipeline):
        if step_matches(step, item.after):
            insert_step = index + 1
            break

        if step_matches(step, item.before):
            insert_step = index
            break

    if insert_step == -1:
        raise ValueError(f"Unable to insert step! Bad item: {item}")
    pipeline.insert(insert_step, name + stringify_param(item.parameters))


def insert_extra_steps(pipeline: list[str], extra_steps):
    for name, value in extra_steps.items():
        if isinstance(value, list):
            for item in value:
                insert_extra_step(pipeline, name, item)
        else:
            insert_extra_step(pipeline, name, value)


def make_pipeline(target: SingleTarget, model_name: str, ctx: StepContext) -> Union[None, str]:
    exporter_option = target.import_method
    if override := target.overrides.get(model_name):
        callback_type = override.callback_type or target.callback_type
        extra_steps = override.extra_steps if override.extra_steps is not None else target.extra_steps
        parameters = override.parameters if override.parameters is not None else target.parameters
        active = override.active if override.active is not None else target.active
        if override.import_method:
            exporter_option = override.import_method
    else:
        callback_type = target.callback_type
        extra_steps = target.extra_steps
        parameters = target.parameters
        active = target.active

    if not active:
        return None

    if exporter_option:
        ctx.exporter = exporter_option
    exporter_valid = ctx.exporter in PIPELINE_BLOCKOUTS[callback_type].exporters
    ctx.exporter_override = (
        ctx.exporter if exporter_valid
        else (PIPELINE_BLOCKOUTS[callback_type].exporters or ["no_exporter"])[0]
    )
    pipeline_blockout = []
    for step in PIPELINE_BLOCKOUTS[callback_type].steps:
        parameter = parameters.get(step.name, True)
        if isinstance(parameter, list) and parameter:
            for item in parameter:
                ctx.parameter = item
                value = step.make_string(ctx)
                if value:
                    pipeline_blockout.append(value)
        else:
            ctx.parameter = parameter
            value = step.make_string(ctx)
            if value:
                pipeline_blockout.append(value)

    insert_extra_steps(pipeline_blockout, extra_steps)
    return " ".join(pipeline_blockout)
