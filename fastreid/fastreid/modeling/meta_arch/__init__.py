# encoding: utf-8
"""
@author:  liaoxingyu
@contact: sherlockliao01@gmail.com
"""

from .build import META_ARCH_REGISTRY, build_model


# import all the meta_arch, so they will be registered
from .baseline import Baseline
from .s9_branch import S9BranchBaseline
from .s10_branch import S10BranchBaseline
from .mgn import MGN
from .moco import MoCo
from .distiller import Distiller
