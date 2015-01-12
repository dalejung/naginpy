import ast
from collections import OrderedDict
from textwrap import dedent
from unittest import TestCase

import nose.tools as nt
import pandas as pd
import numpy as np

from earthdragon.tools.timer import Timer

from naginpy.asttools import ast_print, ast_source, replace_node, _eval

from ..special_eval import SpecialEval
from ..computation import ComputationManager, Computable, _manifest

cm = ComputationManager()

df = pd.DataFrame(np.random.randn(30, 3), columns=['a', 'bob', 'c'])

def some_func(df):
    return df + 100

source = """
pd.rolling_sum(df, 5) + some_func(df.bob) + 1
"""

manifest = _manifest(source, locals())
