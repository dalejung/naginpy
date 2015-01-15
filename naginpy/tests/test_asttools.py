import ast
from unittest import TestCase
from textwrap import dedent

import nose.tools as nt

from ..asttools import (
    _eval,
    _exec,
    _convert_to_expression,
    ast_source,
    ast_equal,
    ast_contains
)

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


def test_ast_equal():
    source = """test(np.random.randn(10, 10))"""
    code1 = ast.parse(source, mode='eval')

    source2 = """test(np.random.randn(10, 10))"""
    code2 = ast.parse(source2, mode='eval')

    nt.assert_true(ast_equal(code1, code2))

    source3 = """test(np.random.randn(10, 11))"""
    code3 = ast.parse(source3, mode='eval')
    nt.assert_false(ast_equal(code1, code3))

    # try subset
    source4 = """np.random.randn(10, 11)"""
    code4 = ast.parse(source4, mode='eval')

    nt.assert_true(ast_equal(code3.body.args[0], code4.body))


def test_ast_contains():
    source1 = """test(np.random.randn(10, 11)) + test2 / 99"""
    code1 = ast.parse(source1, mode='eval').body

    source2 = """np.random.randn(10, 11)"""
    test = ast.parse(source2, mode='eval').body
    nt.assert_true(ast_contains(code1, test))

    test = ast.parse("10", mode='eval').body
    nt.assert_true(ast_contains(code1, test))

    test = ast.parse("test2", mode='eval').body
    nt.assert_true(ast_contains(code1, test))

    test = ast.parse("np.random.randn", mode='eval').body
    nt.assert_true(ast_contains(code1, test))

    test = ast.parse("test2/99", mode='eval').body
    nt.assert_true(ast_contains(code1, test))

    # False. Not that this isn't about a textual subset.
    # random.randn means nothing without np. it implies a 
    # top level random module
    test = ast.parse("random.randn", mode='eval').body
    nt.assert_false(ast_contains(code1, test))

    # test against a module.
    source = """
    first_line() + 100
    bob = test(np.random.randn(10, 11)) + test2 / 99
    """
    mod = ast.parse(dedent(source))

    source2 = """np.random.randn(10, 11)"""
    test = ast.parse(source2, mode='eval').body
    nt.assert_true(ast_contains(mod, test))

def test_ast_contains_expression():
    """
    Test that the fragment must be an expression.
    """
    # test against a module.
    source = """
    first_line() + 100
    bob = test(np.random.randn(10, 11)) + test2 / 99
    """
    mod = ast.parse(dedent(source))

    # expression compiled as module work sfine
    source2 = """np.random.randn(10, 11)"""
    test = ast.parse(source2)
    nt.assert_true(ast_contains(mod, test))

    # assignment is a nono
    with nt.assert_raises_regexp(Exception, "Fragment must be an expression"):
        source2 = """a = np.random.randn(10, 11)"""
        test = ast.parse(source2)
        ast_contains(mod, test)
