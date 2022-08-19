from copy import deepcopy
from typing import Any, Dict, Optional, TextIO

import yaml
from deepmerge import Merger

from kilroy_face_twitter import resource_text

_DEFAULT_MERGER = Merger(
    [(list, ["override"]), (dict, ["merge"]), (set, ["override"])],
    ["override"],
    ["override"],
)


def _merge_configs(
    default_config: Dict[str, Any],
    user_config: Dict[str, any],
    merger: Merger = _DEFAULT_MERGER,
    **kwargs,
) -> Dict[str, Any]:
    config = deepcopy(default_config)
    merger.merge(config, user_config)
    merger.merge(config, kwargs)
    return config


def get_config(f: Optional[TextIO] = None, **kwargs) -> Dict[str, Any]:
    config = yaml.safe_load(resource_text("config.yaml"))
    user_config = yaml.safe_load(f) if f else {}
    return _merge_configs(config, user_config, **kwargs)
