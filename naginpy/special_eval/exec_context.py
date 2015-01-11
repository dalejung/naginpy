import ast

import numpy as np

from naginpy.asttools import (ast_source, _eval, is_load_name,
                              _convert_to_expression)

def _hashable(item):
    try:
        hash(item)
    except TypeError:
        return False
    return True

def _is_scalar(val):
    return np.isscalar(val)

def _obj(val):
    if _is_scalar(val):
        return val
    return val.get_obj()

def _contextify(obj):
    if isinstance(obj, ContextObject):
        return obj

    if _is_scalar(obj):
        return ScalarObject(obj)

    return ContextObject(obj)

class ContextObject(object):
    """ Represents an input arg to an Expression """
    stateless = False

    def __init__(self, obj):
        self.obj = obj

    def get_obj(self):
        return self.obj

    @property
    def key(self):
        return str(id(self.obj))

    def __hash__(self):
        return hash(self.key)

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __repr__(self):
        class_name = self.__class__.__name__
        key = self.key
        return "{class_name}({key})".format(**locals())

class ScalarObject(ContextObject):
    """
    Context object to wrap scalars which are stateless.
    """
    stateless = True

    def __init__(self, obj):
        if not _is_scalar(obj):
            raise TypeError("ScalarObject must wrap scalar")
        self.obj = obj

    @property
    def key(self):
        return repr(self.obj)

def get_source_key(source):
    if hasattr(source, 'source_key'):
        return source.source_key
    return id(source)

class SourceObject(ContextObject):
    """
    Simple Stateless object that can take in a dict
    """
    stateless = True

    def __init__(self, source, key, source_key=None):
        self.source = source
        self._obj_key = key
        if source_key is None:
            source_key = get_source_key(source)
        self.source_key = source_key

    def get_obj(self):
        return self.source.get(self._obj_key)

    @property
    def key(self):
        return "{0}::{1}".format(self.source_key, self._obj_key)

def ns_hashset(context):
    """ Return a frozenset used for creating ExecutionContext hash """
    return frozenset({k: v for k, v in context.items()}.items())

class ExecutionContext(object):
    """
    ExecutionContext is dict like context where the items
    have to hashable so that the ExecutionContext itself is
    hashable.


    Note that an ExecutionContext can have items whose hash depends on
    id(). This would make the EC stateful. A Stateless EC will require
    nothing but stateless items.

    TODO: do we consider scalar stateless? If so, then we need to store the
    actual scalar values in context.

    Technically, we could pickle small objects and then they would be stateless.

    Obviously we would not want to pickle DataFrames/ndarrays.

    Really need to figure out the interplay here. Maybe a stateless
    ContextObject has an api similar to pickling. So small objects could
    save their entire state, and bigger source objects could just store
    the data needed to reconstruct.

    Technically we quasi support this since you could embed pickled data
    within key.

    Though this is more of a question of whether to automatically pickle
    small objects that don't explicitly handle special_eval
    """
    def __init__(self, data=None):
        if data is None:
            data = {}

        if isinstance(data, ExecutionContext):
            # ?? not sure about copy semantics
            data = data.data.copy()

        self._wrap_scalars(data)

        self._validate_data(data)

        self.data = data

    @property
    def stateless(self):
        return all(map(lambda x: x.stateless, self.data.values()))

    def _validate_data(self, data):
        for k, v in data.items():
            if _is_scalar(v):
                raise TypeError("scalar values must be wrapped")

            if not isinstance(v, ContextObject):
                raise TypeError("Non-scalar objects must be a ContextObject")

    def __hash__(self):
        return hash(ns_hashset(self.data))

    def __eq__(self, other):
        if isinstance(other, ExecutionContext):
            return hash(self) == hash(other)
        if isinstance(other, dict):
            return hash(self) == hash(ExecutionContext(other))
        raise Exception("ExecutionContext can only compare to ExecutionContext"
                        " or dict. Given type {type}".format(type=type(other)))

    @classmethod
    def _wrap_scalars(self, data):
        for k in data:
            obj = data[k]
            if _is_scalar(obj):
                data[k] = ScalarObject(obj)

    @classmethod
    def _wrap_context(self, ns, keys=None):
        if keys is None:
            keys = ns.keys()

        data = {}
        for k in keys:
            obj = ns[k]
            data[k] = _contextify(obj)

        return data

    @classmethod
    def from_ns(cls, ns, keys=None):
        """
        Will wrap a namespace and create ContextObjects that point to the
        object in kernel.
        """
        data = cls._wrap_context(ns, keys=keys)
        return cls(data)

    def items(self):
        return self.data.items()

    def values(self):
        return self.data.values()

    def extract(self):
        """
        Get the actual values from execution context
        """
        out = {}
        for k, v in self.data.items():
            out[k] = _obj(v)

        return out

    def __repr__(self):
        bits = []
        for k in sorted(self.data):
            bits.append("{0}={1}".format(k, self.data[k]))
        _dict = ", ".join(bits)
        return "{0}({1})".format(self.__class__, _dict)
