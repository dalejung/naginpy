import ast
from unittest import TestCase

import numpy as np
from numpy.testing import assert_almost_equal
import nose.tools as nt

from ..manifest import (ContextObject, SourceObject, Expression, Manifest,
                        get_source_key)


class TestContextObject(TestCase):
    def test_context_object(self):
        obj = object()

        co = ContextObject(obj)
        assert co.key == str(id(obj))
        assert hash(co) == hash(str(id(obj)))
        assert co.get_obj() is obj


class TestSourceObject(TestCase):
    def test_source_context(self):
        """
        """
        obj = object()
        source_dict = {}
        source_dict['test'] = obj
        source_dict['test2'] = object()
        source_dict['test3'] = object()

        so = SourceObject(source_dict, 'test', 'source_dict')
        so_copy = SourceObject(source_dict, 'test', 'source_dict')
        nt.assert_equal(so.key, 'source_dict::test', "composite keys should"
                        " follow standard combination")

        nt.assert_is(so.get_obj(), obj, "in this case, should return exact copy")

        so2 = SourceObject(source_dict, 'test2', 'source_dict')
        so3 = SourceObject(source_dict, 'test3', 'source_dict')

        # test __eq__
        nt.assert_equal(so, so_copy)
        nt.assert_not_equal(so, so2)
        nt.assert_not_equal(so, so3)

    def test_stateless_source(self):
        """
        Test that stateless objects will work with sources that
        don't return the same in memory object
        """

        class ArangeSource(object):
            """
            Will just return an np.arange(key)
            """
            source_key = 'aranger'
            def __init__(self):
                pass

            def get(self, key):
                return np.arange(key)

        aranger = ArangeSource()
        nt.assert_equal(get_source_key(aranger), 'aranger')
        so = SourceObject(aranger, 10)
        assert_almost_equal(so.get_obj(), np.arange(10))
        obj1 = so.get_obj()
        obj2 = so.get_obj()

        nt.assert_is_not(obj1, obj2)
        assert_almost_equal(obj1, obj2)


    def test_get_source_key(self):
        """
        Test that source_key attr works
        """
        class Source(object):
            def __init__(self, data, source_key):
                self.data = data
                self.source_key = source_key

            def get(self, key):
                return self.data[key]

        obj = object()
        source_dict = {}
        source_dict['test'] = obj
        source = Source(source_dict, 'sk_attr')

        so = SourceObject(source, 'test')
        assert so.key == 'sk_attr::test'


def grab_expression_from_assign(code):
    node = code.body[0].value
    expr = ast.Expression(lineno=0, col_offset=0, body=node)
    return expr

source = """
arr = np.arange(20)
res = np.sum(arr)
"""
lines = source.strip().split('\n')
load_names = [['np'], ['np', 'arr']]
for i, line in enumerate(lines):
    code = ast.parse(line, '<>', 'exec')

    with nt.assert_raises(Exception):
        print(code.body[0])
        Expression(code.body[0])

    extracted_expr = grab_expression_from_assign(code)
    # skip the assign
    base_expr = ast.parse(line.split('=')[1].strip(), mode='eval')
    exp1 = Expression(extracted_expr)
    exp2 = Expression(base_expr)
    nt.assert_equal(exp1, exp2)
    nt.assert_is_not(exp1, exp2)
    nt.assert_count_equal(exp1.load_names(), load_names[i])

