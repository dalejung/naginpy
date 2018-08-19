import ast
from collections import OrderedDict
from textwrap import dedent
from unittest import TestCase

import nose.tools as nt
import pandas as pd
import pandas.util.testing as tm
import numpy as np

from asttools import ast_print, ast_source, replace_node, _eval

from ..special_eval import SpecialEval
from ..computation import ComputationManager, Computable, _manifest
from ..exec_context import _contextify


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

        source = "df.rolling(5).sum()"
        entry = cm_get(cm, source, locals(), globals())
        # context should only include vars needed by expression
        nt.assert_set_equal(set(entry.context.keys()), set(entry.expression.load_names()))

        # should get same entry back
        entry2 = cm.get(source, locals())
        nt.assert_is(entry, entry2)

    def test_execute(self):
        cm = ComputationManager()

        df = pd.DataFrame(np.random.randn(30, 3), columns=['a', 'bob', 'c'])
        source = "df.rolling(5).sum()"
        entry = cm_get(cm, source, locals(), globals())

        # execute first time
        val = cm.execute(entry)
        correct = df.rolling(5).sum()

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
        source = "df.rolling(5).sum()"
        entry = cm_get(cm, source, locals(), globals())

        # execute first time
        val = cm.execute(entry)
        entry2 = cm.by_value(val)
        nt.assert_is(entry2.value, val)

    def test_nested_entries(self):
        cm = ComputationManager()
        df = pd.DataFrame(np.random.randn(30, 3), columns=['a', 'bob', 'c'])
        source = """pd.core.window.Rolling(np.log(df + 10), 5, min_periods=1).sum()"""
        ns = locals()
        entry = cm_get(cm, source, ns, globals())
        code = entry.expression.code

        entry2 = cm_get(cm, "np.log(df+10)", ns, globals())
        val2 = cm.execute(entry2)
        tm.assert_frame_equal(np.log(df+10), val2)

        getter, ns_update = cm.generate_getter_node(entry2)
        with nt.assert_raises(NameError):
            getter_val = _eval(getter, ns)

        ns.update(ns_update)
        getter_val = _eval(getter, ns)
        # running the getter node with updated ns should return exact same value
        nt.assert_is(getter_val, val2)

        code.body.args[0] = getter
        # note that the entry expression was changed, but the entry context was not
        with nt.assert_raises(NameError):
            cm.execute(entry)

        # TODO, so https://github.com/dalejung/naginpy/issues/2
        # having to mutate the manifest doesn't seem like a great idea.
        # need to re-think this api
        entry.context.data.update(__defer_manager__=_contextify(ns['__defer_manager__']))
        cm.execute(entry)
