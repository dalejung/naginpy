import ast
from unittest import TestCase

import numpy as np
import pandas as pd
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

from .common import ArangeSource

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
        aranger = ArangeSource()
        nt.assert_equal(get_source_key(aranger), 'aranger')
        so = SourceObject(aranger, 10)
        assert_almost_equal(so.get_obj(), np.arange(10))
        obj1 = so.get_obj()
        obj2 = so.get_obj()

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

    def test_extract(self):
        aranger = ArangeSource()

        so10 = SourceObject(aranger, 10)
        so20 = SourceObject(aranger, 20)
        so30 = SourceObject(aranger, 30)

        context = {
            'd': 13,
            'str': 'string_Test' * 20,
            'arr': np.random.randn(10),
            'so10': so10,
            'so20': so20,
            'so30': so30
        }

        # creating the source object does not auto create
        nt.assert_equal(len(aranger.cache), 0)

        exec_context = ExecutionContext.from_ns(context)

        data = exec_context.extract()

        # extract grabbed the data
        nt.assert_equal(len(aranger.cache), 3)
        nt.assert_set_equal(set(map(lambda x: x[0], aranger.cache.keys())), 
                            set([10, 20, 30]))

        # regular context object should be identity
        nt.assert_is(context['arr'], data['arr'])

        for i in [10, 20, 30]:
            k = 'so'+str(i)
            test = np.arange(i)
            # not same
            nt.assert_is_not(data[k], test)
            # but equal
            assert_almost_equal(data[k], test)

    def test_repr(self):
        aranger = ArangeSource()

        so10 = SourceObject(aranger, 10)
        so20 = SourceObject(aranger, 20)
        so30 = SourceObject(aranger, 30)

        context = {
            'd': 13,
            'str': 'string_Test' * 20,
            'arr': np.random.randn(10),
            'so10': so10,
            'so20': so20,
            'so30': so30
        }

        exec_context = ExecutionContext.from_ns(context)

        repr1 = repr(exec_context)

        context['d'] = 12

        exec_context = ExecutionContext.from_ns(context)
        repr2 = repr(exec_context)

        # change in value should be reflected
        nt.assert_not_equal(repr1, repr2)

        context = {
            'so20': so20,
            'so30': so30
        }
        context['so10'] = so10
        context['arr'] = np.arange(10)
        context['d'] = 13
        context['str'] = 'string_Test' * 20

        exec_context = ExecutionContext.from_ns(context)
        repr3 = repr(exec_context)

        context['arr'] = np.arange(10)
        exec_context = ExecutionContext.from_ns(context)
        repr4 = repr(exec_context)

        # since np.arange is wrapped in ContextObject, it fails id check
        nt.assert_not_equal(repr3, repr4)

        # mix up order? still same context
        del context['so10']
        del context['so20']
        del context['d']
        context['so10'] = so10
        context['so20'] = so20
        context['d'] = 13

        exec_context = ExecutionContext.from_ns(context)
        repr5 = repr(exec_context)

        nt.assert_equal(repr4, repr5)

    def test_hashset(self):
        aranger = ArangeSource()

        so10 = SourceObject(aranger, 10)
        so20 = SourceObject(aranger, 20)
        so30 = SourceObject(aranger, 30)

        context = {
            'd': 13,
            'str': 'string_Test' * 20,
            'arr': np.random.randn(10),
            'so10': so10,
            'so20': so20,
            'so30': so30
        }

        exec_context = ExecutionContext.from_ns(context)

        hashset = exec_context.hashset()
        nt.assert_equal(hash(hashset), hash(exec_context))

    def test_iter(self):
        context = {
            'd': 13,
            'str': 'string_Test',
        }

        exec_context = ExecutionContext.from_ns(context)
        correct = list(exec_context.keys())
        test = list(exec_context)
        nt.assert_count_equal(test, correct)

    def test_getitem(self):
        context = {
            'd': 13,
            'str': 'string_Test',
        }

        exec_context = ExecutionContext.from_ns(context)
        for k in exec_context:
            nt.assert_is(exec_context[k].get_obj(), context[k])

    def test_key(self):
        context = {
            'd': 13,
            'str': 'string_Test'
        }

        exec_context = ExecutionContext.from_ns(context)
        correct = "d=ScalarObject(13), str=ScalarObject('string_Test')"
        nt.assert_equal(exec_context.key, correct)

    def test_mutable(self):
        context = {
            'd': 13,
            'str': 'string_Test'
        }

        exec_context = ExecutionContext.from_ns(context)
        with nt.assert_raises(Exception):
            exec_context['test'] = 123

        # works fine
        exec_context = ExecutionContext.from_ns(context, mutable=True)
        exec_context['test'] = ScalarObject(123)

        # will only accept ManifestABC types. might consider autoboxing?
        with nt.assert_raises(TypeError):
            exec_context['bad'] = 123

class TestModuleContext(TestCase):
    def test_module_context(self):
        import pandas.util.testing as tm
        import pandas as pd
        context = {
            'tm': tm
        }

        exec_context = ExecutionContext.from_ns(context)

        tm_mod = exec_context.data['tm']
        correct = "pandas.util.testing(pandas={version})"
        correct = correct.format(version=pd.__version__)

        nt.assert_equal(tm_mod.key, correct)
