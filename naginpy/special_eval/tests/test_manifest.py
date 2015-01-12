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

from .common import ArangeSource

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
    def test_key(self):
        """ stable hash key """
        source = """
        np.arange(20)
        np.sum(arr)
        """
        source = dedent(source)
        code = ast.parse(source)

        expr1 = Expression(code.body[0])
        expr2 = Expression(code.body[1])

        correct1 = b'}\xff\x1c\x0er\xe8k3\x84\x96R\x98\x9a\xa4\xe0i'
        correct2 = b'\xd6\x88\x08\xa2\xd0\x01\xa4\xc6\xabb\x1aTj\xce\x98\x18'
        # keys are stable and should not change between lifecycles
        nt.assert_equal(expr1.key, correct1)
        nt.assert_equal(expr2.key, correct2)


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

    def test_nested_eval(self):
        """
        d * (1 + arr + arr2[10:])
        which is really two manifests

        arr_manifest = (1 + arr + arr2[10:])
        manfiest = (d * (arr_manifest))
        """

        arr_source = "1 + arr + arr2[10:]"
        aranger = ArangeSource()

        arr_context = {
            'arr': SourceObject(aranger, 10),
            'arr2': SourceObject(aranger, 20),
        }
        arr_expr = Expression(arr_source)
        arr_exec_context = ExecutionContext.from_ns(arr_context)
        arr_manifest = Manifest(arr_expr, arr_exec_context)

        source = "d * arr"
        context = {
            'd': 13,
            'arr': arr_manifest
        }
        expr = Expression(source)
        exec_context = ExecutionContext.from_ns(context)
        manifest = Manifest(expr, exec_context)

        correct = 13 * (1 + np.arange(10) + np.arange(20)[10:])

        # up till this point, everything is lazy
        nt.assert_equal(len(aranger.cache), 0)
        assert_almost_equal(correct, manifest.eval())
        nt.assert_equal(len(aranger.cache), 2)

import hashlib

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
expr1 = Expression(code.body[0])
expr2 = Expression(code.body[1])
