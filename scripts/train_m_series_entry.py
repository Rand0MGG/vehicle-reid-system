# encoding: utf-8
"""Train entry for M-series configs without globally importing the new head."""

import functools
import inspect
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FASTREID_ROOT = REPO_ROOT / "fastreid"
TOOLS_DIR = FASTREID_ROOT / "tools"

sys.path.insert(0, str(TOOLS_DIR))
sys.path.insert(0, str(FASTREID_ROOT))

import fastreid.config as fastreid_config
import fastreid.config.config as config_mod


def _m_series_configurable(init_func=None, *, from_config=None):
    """Runtime-local configurable decorator without FastReID docstring assertion."""

    if init_func is not None:
        assert (
            inspect.isfunction(init_func)
            and from_config is None
            and init_func.__name__ == "__init__"
        ), "Incorrect use of @configurable."

        @functools.wraps(init_func)
        def wrapped(self, *args, **kwargs):
            try:
                from_config_func = type(self).from_config
            except AttributeError as exc:
                raise AttributeError(
                    "Class with @configurable must have a 'from_config' classmethod."
                ) from exc
            if not inspect.ismethod(from_config_func):
                raise TypeError(
                    "Class with @configurable must have a 'from_config' classmethod."
                )

            if config_mod._called_with_cfg(*args, **kwargs):
                explicit_args = config_mod._get_args_from_config(
                    from_config_func, *args, **kwargs
                )
                init_func(self, **explicit_args)
            else:
                init_func(self, *args, **kwargs)

        return wrapped

    if from_config is None:
        return _m_series_configurable
    assert inspect.isfunction(from_config), "from_config must be a function."

    def wrapper(orig_func):
        @functools.wraps(orig_func)
        def wrapped(*args, **kwargs):
            if config_mod._called_with_cfg(*args, **kwargs):
                explicit_args = config_mod._get_args_from_config(
                    from_config, *args, **kwargs
                )
                return orig_func(**explicit_args)
            return orig_func(*args, **kwargs)

        return wrapped

    return wrapper


# Patch only this process before importing the M-series head.
config_mod.configurable = _m_series_configurable
fastreid_config.configurable = _m_series_configurable

import fastreid.modeling.heads.residual_mlp_embedding_head  # noqa: F401,E402
import train_net  # noqa: E402

from fastreid.engine import default_argument_parser, launch  # noqa: E402


if __name__ == "__main__":
    args = default_argument_parser().parse_args()
    print("Command Line Args:", args)
    print("M-series head registered in runtime entry.")
    launch(
        train_net.main,
        args.num_gpus,
        num_machines=args.num_machines,
        machine_rank=args.machine_rank,
        dist_url=args.dist_url,
        args=(args,),
    )
