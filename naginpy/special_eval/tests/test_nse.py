import ast
from unittest import TestCase
from textwrap import dedent

import pandas as pd
import numpy as np
from nose.tools import raises

from ..nse import NSEEngine, nse
from ..special_eval import SpecialEval
from ..engine import NormalEval

class _NSE(object):

    @nse
    def string_eval(self, var):
        return var

    def non_nse(self, var):
        return var

def run_nse(ns, source):
    source = dedent(source)
    ns = ns.copy()
    se = SpecialEval(source, ns=ns, engines=[NSEEngine(), NormalEval()])
    out = se.process()
    return ns

class TestNSE(TestCase):

    def test_default_nse(self):
        """
        Test that functions with @nse wrapper change their inputs
        to strings
        """

        @nse
        def string_func(var):
            return var

        def normal_func(var):
            return var

        source = """
        l = dale.string_eval(dale)
        df_string = dale.string_eval(df.iloc[:, :])
        i = dale.non_nse(123)
        i2 = dale.string_eval(123)

        int_string = string_func(123)
        int_int = normal_func(123)
        """

        dale = _NSE()
        df = pd.DataFrame()

        ns = run_nse(locals(), source)

        assert ns['l'] == 'dale'
        assert ns['df_string'] == 'df.iloc[:, :]'
        assert ns['i'] == 123
        assert ns['i2'] == '123'
        assert ns['int_string'] == '123'
        assert ns['int_int'] == 123

    # TODO this should not raise in the future
    @raises(SyntaxError)
    def test_full_nse(self):
        """
        x~y is not proper python syntax, so currently it will fail ast.parse.

        Eventually we want our own ast builder that will replace certain
        broken syntax with a custom ast.AST that can be handled by our nse
        and replace it with a string.
        """

        source = """
        l = dale.string_eval(x~y)
        """

        ns = run_nse(locals(), source)

        assert ns['l'] == 'x~y'


source = """
i = dale.non_nse(123)
l = dale.string_eval(dale)
d = dale.string_eval(df.iloc[:, :])
"""

dale = _NSE()
df = pd.DataFrame()

ns = run_nse(locals(), source)


if __name__ == '__main__':
    import nose
    nose.runmodule(argv=[__file__, '-vvs', '-x', '--pdb', '--pdb-failure'],
                    exit=False)
