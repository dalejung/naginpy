import ast
from unittest import TestCase

import numpy as np
from numpy.testing import assert_almost_equal
import nose.tools as nt

from ..exec_context import (
    ContextObject,
    SourceObject,
    ScalarObject,
    ExecutionContext,
    _obj,
    get_source_key
)


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


class TestExecutionContext(TestCase):

    def test_scalar_values(self):
        """
        scalars are valid objects since they are hashable
        right now they are auto wrapped
        """
        context = {
            'd': 13,
            'str': 'string_Test'
        }

        exec_context = ExecutionContext(context)
        for k, v in exec_context.items():
            nt.assert_is_instance(v, ScalarObject)
            nt.assert_true(v.stateless)

        nt.assert_true(exec_context.stateless)

    def test_init_context_object(self):
        """
        Passed in data must be scalar or context object
        """
        context = {
            'arr': np.random.randn(10)
        }
        with nt.assert_raises(TypeError):
            exec_context = ExecutionContext(context)

    def test_from_ns(self):
        context = {
            'd': 13,
            'str': 'string_Test',
            'arr': np.random.randn(10)
        }

        exec_context = ExecutionContext.from_ns(context)
        for k, v in exec_context.items():
            nt.assert_is(_obj(v), context[k])

        # since arr is not stateless, entire context is stateful
        nt.assert_false(exec_context.stateless)

    def test_equals(self):
        source_dict = {}
        obj = object()
        source_dict['test'] = obj

        so = SourceObject(source_dict, 'test', 'source_dict')
        so_copy = SourceObject(source_dict, 'test', 'source_dict')

        context = {
            'd': 13,
            'str': 'string_Test' * 20,
            'arr': np.random.randn(10),
            'source': so
        }
        context2 = context.copy()
        context2['source'] = so_copy

        exec_context = ExecutionContext.from_ns(context)
        exec_context2 = ExecutionContext.from_ns(context2)
        nt.assert_equal(exec_context, exec_context2)

source_dict = {}
obj = object()
source_dict['test'] = obj

so = SourceObject(source_dict, 'test', 'source_dict')
so_copy = SourceObject(source_dict, 'test', 'source_dict')

context = {
    'd': 13,
    'str': 'string_Test' * 20,
    'arr': np.random.randn(10),
    'source': so
}
context2 = context.copy()
context2['source'] = so_copy

exec_context = ExecutionContext.from_ns(context)
exec_context2 = ExecutionContext.from_ns(context2)
nt.assert_equal(exec_context, exec_context2)
