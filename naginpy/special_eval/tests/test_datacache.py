import ast
from collections import OrderedDict
from textwrap import dedent

import pandas as pd
import numpy as np

from earthdragon.tools.timer import Timer

from naginpy.asttools import ast_print, ast_source, replace_node, _eval

from ..special_eval import SpecialEval
from ..engine import Engine, NormalEval
from ..datacache import DataCacheEngine
from ..computation import ComputationManager


class Dale(object):

    def tail(self, var):
        return var

class slow_func(object):

    def __init__(self):
        self.count = 0

    def __call__(self, df):
        import time
        #time.sleep(5)
        self.count += 1
        return df

def run_datacache(ns, global_ns, source):
    source = dedent(source)
    ns = ns.copy()
    ns.update({k: v for k, v in global_ns.items() if k not in ns})
    dm = ComputationManager()
    dc = DataCacheEngine(dm)
    ns['dm'] = dm
    ns['dc'] = dc

    se = SpecialEval(source, ns=ns, engines=[dc, NormalEval()])
    out = se.process()
    return ns

def test_hot_cache():
    df = pd.DataFrame(np.random.randn(30, 3), columns=['a', 'bob', 'c'])
    dale = Dale()

    some_func = slow_func()
    source = """
    res = pd.rolling_sum(df, 5) + some_func(df.bob) + 1
    res2 = pd.rolling_sum(df, 5) + some_func(df.bob) + 1
    """

    ns = run_datacache(locals(), globals(), source)

    assert id(ns['res']) == id(ns['res2'])
    assert some_func.count == 1

def test_changed_context():
    """
    Testing that changing the execution context causes the results to change
    """
    df = pd.DataFrame(np.random.randn(30, 3), columns=['a', 'bob', 'c'])
    dale = Dale()

    some_func = slow_func()
    source = """
    res = pd.rolling_sum(df, 5) + some_func(df.bob) + 1
    # change calling context by replacing df
    df = pd.DataFrame(np.random.randn(30, 3), columns=['a', 'bob', 'c'])
    res2 = pd.rolling_sum(df, 5) + some_func(df.bob) + 1
    """

    ns = run_datacache(locals(), globals(), source)

    assert id(ns['res']) != id(ns['res2'])
    assert some_func.count == 2
