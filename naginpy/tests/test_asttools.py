import ast
from unittest import TestCase
from textwrap import dedent

import nose.tools as nt

from ..asttools import _eval, _exec, _convert_to_expression, ast_source

class TestEval(TestCase):
    def test_exec(self):
        source = """
        d = 123
        """
        code = ast.parse(dedent(source))
        ns = {}
        out = _exec(code.body[0], ns)
        nt.assert_equal(ns['d'], 123)
        nt.assert_is_none(out)

        # eval versio of exec
        source = """
        123
        """
        code = ast.parse(dedent(source))
        ns = {}
        out = _exec(code.body[0], ns)
        nt.assert_equal(out, 123)

    def test_eval(self):
        """
        _eval should only run on expressions
        """
        source = """
        d = 123
        """
        code = ast.parse(dedent(source))
        ns = {}
        with nt.assert_raises(Exception):
            out = _eval(code.body[0], ns)

def test_ast_source_expression():
    """ expressions were having a problem in astor """
    source = """np.random.randn(10, 10)"""
    code = ast.parse(dedent(source))

    expr = _convert_to_expression(code)
    nt.assert_equal(source, ast_source(expr))
