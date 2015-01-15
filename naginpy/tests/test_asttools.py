import ast
from unittest import TestCase
from textwrap import dedent

import pandas as pd
import numpy as np
import nose.tools as nt

from ..asttools import (
    _eval,
    _exec,
    _convert_to_expression,
    ast_source,
    ast_equal,
    ast_contains,
    code_context_subset,
    graph_walk
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

def test_ast_contains_ignore_names():
    # test against a module.
    source = """
    test(np.random.randn(10, 11))
    """
    mod = ast.parse(dedent(source))

    # rename np to test
    source2 = """test.random.randn(10, 11)"""
    test = ast.parse(source2)
    nt.assert_true(ast_contains(mod, test, ignore_var_names=True))

    # note that only Load(ctx.Load) ids will be ignored
    source2 = """test.text"""
    test = ast.parse(source2)
    nt.assert_false(ast_contains(mod, test, ignore_var_names=True))

    # dumb example. single Name will always match
    source2 = """anything"""
    test = ast.parse(source2)
    nt.assert_true(ast_contains(mod, test, ignore_var_names=True))

def test_ast_graph_walk():
    source = """
    test(np.random.randn(10, 11))
    """
    mod = ast.parse(dedent(source))

    items = list(graph_walk(mod))
    graph_nodes = [item['node'] for item in items]

    walk_nodes = list(ast.walk(mod))
    # remove module node which the graph_walk won't have
    nt.assert_is_instance(walk_nodes.pop(0), ast.Module)

    # we should have reached the same nodes, not in same order
    nt.assert_count_equal(graph_nodes, walk_nodes)

    graph_types = [
        ast.Expr,
        ast.Call,
        ast.Name,
        ast.Load,
        ast.Call,
        ast.Attribute,
        ast.Attribute,
        ast.Name,
        ast.Load,
        ast.Load,
        ast.Load,
        ast.Num,
        ast.Num
    ]

    # using type order to check that the type ordering is stable..
    nt.assert_list_equal(list(map(type, graph_nodes)), graph_types)

def test_code_context_subset():
    df = pd.DataFrame(np.random.randn(30, 3), columns=['a', 'bob', 'c'])
    ns = {
        'df': df,
        'c': 1,
        'pd': pd,
        'np': np
    }
    source = """pd.rolling_sum(np.log(df + 10), 5, min_periods=c)"""
    code = ast.parse(dedent(source), mode='eval')

    # use blah instead of df. same code.
    child_ns = ns.copy()
    child_ns['blah'] = ns['df']
    child_code = ast.parse("np.log(blah+10)") # note that df was renamed blah

    nt.assert_is_none(code_context_subset(code, ns, child_code, child_ns,
                                        ignore_var_names=False))

    # ignoring the var names should get us our match
    item = code_context_subset(code, ns, child_code, child_ns,
                            ignore_var_names=True)
    nt.assert_is_not_none(item)

    field_name = 'args'
    field_index = 0
    correct = getattr(code.body, field_name)[field_index]
    nt.assert_is(item['node'], correct)
    nt.assert_is(item['parent'], code.body)
    nt.assert_equal(item['field_name'], field_name)
    nt.assert_equal(item['field_index'], field_index)
