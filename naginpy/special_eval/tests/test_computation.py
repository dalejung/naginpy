import ast
from collections import OrderedDict
from textwrap import dedent
from unittest import TestCase

import nose.tools as nt
import pandas as pd
import pandas.util.testing as tm
import numpy as np

from earthdragon.tools.timer import Timer

from naginpy.asttools import ast_print, ast_source, replace_node, _eval

from ..special_eval import SpecialEval
from ..computation import ComputationManager, Computable, _manifest


def some_func(df):
    return df + 100

df = pd.DataFrame(np.random.randn(30, 3), columns=['a', 'bob', 'c'])

def cm_get(cm, source, ns, global_ns):
    """ mix locals and globals """
    ns.update({k:v for k, v in global_ns.items() if k not in ns})
    return cm.get(source, ns)

class TestComputationManager(TestCase):
    def test_get(self):
        cm = ComputationManager()

        source = "pd.rolling_sum(df, 5)"
        entry = cm_get(cm, source, locals(), globals())
        # context should only include vars needed by expression
        nt.assert_set_equal(set(entry.context.keys()), set(entry.expression.load_names()))

        # should get same entry back
        entry2 = cm.get(source, locals())
        nt.assert_is(entry, entry2)

    def test_execute(self):
        cm = ComputationManager()

        df = pd.DataFrame(np.random.randn(30, 3), columns=['a', 'bob', 'c'])
        source = "pd.rolling_sum(df, 5)"
        entry = cm_get(cm, source, locals(), globals())

        # execute first time
        val = cm.execute(entry)
        correct = pd.rolling_sum(df, 5)

        nt.assert_is_not(val, correct)
        tm.assert_frame_equal(val, correct)

        # execute again should return existing value
        val2 = cm.execute(entry)
        nt.assert_is(val, val2)

        entry2 = cm_get(cm, source, locals(), globals())
        nt.assert_is(entry, entry2)
        nt.assert_true(entry2.executed)

        # override keyword
        val3 = cm.execute(entry, override=True)
        nt.assert_is_not(val, val3)
        tm.assert_frame_equal(val, val3)
        cm = ComputationManager()

    def test_by_value(self):
        cm = ComputationManager()

        df = pd.DataFrame(np.random.randn(30, 3), columns=['a', 'bob', 'c'])
        source = "pd.rolling_sum(df, 5)"
        entry = cm_get(cm, source, locals(), globals())

        # execute first time
        val = cm.execute(entry)
        entry2 = cm.by_value(val)
        nt.assert_is(entry2.value, val)


cm = ComputationManager()
df = pd.DataFrame(np.random.randn(30, 3), columns=['a', 'bob', 'c'])
source = "pd.rolling_sum(df, 5)"
entry = cm.get(source, locals())
# context should only include vars needed by expression
nt.assert_set_equal(set(entry.context.keys()), set(entry.expression.load_names()))

val = cm.execute(entry)
correct = pd.rolling_sum(df, 5)

nt.assert_is_not(val, correct)
tm.assert_frame_equal(val, correct)

# caches
val2 = cm.execute(entry)
nt.assert_is(val, val2)

entry2 = cm.get(source, locals())
nt.assert_is(entry, entry2)
nt.assert_true(entry2.executed)

val3 = cm.execute(entry, override=True)
nt.assert_is_not(val, val3)
tm.assert_frame_equal(val, val3)
