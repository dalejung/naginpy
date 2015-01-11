import ast
from unittest import TestCase
from textwrap import dedent

import numpy as np
from numpy.testing import assert_almost_equal
import nose.tools as nt

from ..manifest import (
    Expression,
    Manifest,
)

from ..exec_context import (
    ContextObject,
    SourceObject,
    ExecutionContext,
    get_source_key
)


def grab_expression_from_assign(code):
    node = code.body[0].value
    expr = ast.Expression(lineno=0, col_offset=0, body=node)
    return expr

class TestExpression(TestCase):
    def test_expression(self):
        source = """
        arr = np.arange(20)
        res = np.sum(arr)
        """
        source = dedent(source)
        lines = source.strip().split('\n')
        load_names = [['np'], ['np', 'arr']]
        for i, line in enumerate(lines):
            code = ast.parse(line, '<>', 'exec')

            # expression must be evaluable, assignments are not
            with nt.assert_raises(Exception):
                Expression(code.body[0])

            extracted_expr = grab_expression_from_assign(code)
            # skip the assign
            base_expr = ast.parse(line.split('=')[1].strip(), mode='eval')
            exp1 = Expression(extracted_expr)
            exp2 = Expression(base_expr)
            nt.assert_equal(exp1, exp2)
            nt.assert_is_not(exp1, exp2)
            nt.assert_count_equal(exp1.load_names(), load_names[i])


    def test_single_line(self):
        """ Expressoins can only be single line """
        source = """
        np.arange(20)
        np.sum(arr)
        """
        source = dedent(source)
        code = ast.parse(source)

        # expression must be single line
        with nt.assert_raises(Exception):
            Expression(code)

        # single line still works
        Expression(code.body[0])
        Expression(code.body[1])

    def test_expression_conversion(self):
        """
        So I'm not 100% sure on converting all code into ast.Expressions.
        Right now it is what I'm doing, so might as well explicitly test?
        """
        source = """
        np.arange(20)
        np.sum(arr)
        """
        source = dedent(source)
        code = ast.parse(source)

        expr1 = Expression(code.body[0])
        nt.assert_is_instance(expr1.code, ast.Expression)
        expr2 = Expression(code.body[1])
        nt.assert_is_instance(expr2.code, ast.Expression)

        expr3 = Expression("np.arange(15)")
        nt.assert_is_instance(expr3.code, ast.Expression)


class TestManifest(TestCase):
    def test_eval(self):
        source = "d * string_test"

        context = {
            'd': 13,
            'string_test': 'string_test'
        }

        expr = Expression(source)
        exec_context = ExecutionContext(context)
        manifest = Manifest(expr, exec_context)
        nt.assert_equal(manifest.eval(), 'string_test' * 13)

    def test_equals(self):
        source = "d * string_test"

        context = {
            'd': 13,
            'string_test': 'string_test'
        }

        expr = Expression(source)
        exec_context = ExecutionContext(context)
        manifest = Manifest(expr, exec_context)
        manifest2 = Manifest(expr, exec_context)

        nt.assert_equal(manifest, manifest2)

        # change expression
        expr3 = Expression("d * string_test * 2")
        manifest3 = Manifest(expr3, exec_context)
        nt.assert_not_equal(manifest, manifest3)

        # change context
        context4 = {
            'd': 11,
            'string_test': 'string_test'
        }
        exec_context4 = ExecutionContext(context4)
        manifest4 = Manifest(expr, exec_context4)
        nt.assert_not_equal(manifest, manifest4)
