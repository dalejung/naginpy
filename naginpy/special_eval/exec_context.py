import ast
import types

import numpy as np

from naginpy.special_eval.manifest_abc import ManifestABC
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
    if isinstance(obj, ManifestABC):
        return obj

    if isinstance(obj, types.ModuleType):
        return ModuleContext(obj)

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

ManifestABC.register(ContextObject)

def _version(mod):
    version = getattr(mod, '__version__', None) \
              or getattr(mod, 'version', None)
    return version

def _get_versions(mod):
    """
    Return a list of tuple([pkg_name, version]) for each
    package that effects this module.

    Right now this just grabs from its own package hierarchy.

    I can imagine expanding this like ala pd.show_versions() so
    we can better assured we get the same behavior
    """
    versions = []

    while True:
        version = _version(mod)
        if version:
            versions.append((mod.__name__, version))

        parent_name, _, name = mod.__name__.rpartition('.')
        if not parent_name:
            break
        mod = __import__(parent_name)

    return versions


class ModuleContext(ContextObject):
    stateless = True

    @property
    def key(self):
        return self.get_module_manifest(self.obj)

    @staticmethod
    def get_module_manifest(obj):
        name = obj.__name__
        versions = _get_versions(obj)
        vbits = ["{0}={1}".format(*item) for item in sorted(versions)]
        v_string = ", ".join(vbits)
        key = "{name}({v_string})".format(name=name, v_string=v_string)
        return key


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
    def __init__(self, data=None, mutable=False):
        if data is None:
            data = {}

        if isinstance(data, ExecutionContext):
            # ?? not sure about copy semantics
            data = data.data.copy()

        self._wrap_scalars(data)

        self._validate_data(data)

        self.data = data
        self.mutable = mutable

    def copy(self, mutable=False):
        data = self.data.copy()
        obj = self.__class__(data, mutable=mutable)
        return obj

    @property
    def stateless(self):
        return all(map(lambda x: x.stateless, self.data.values()))

    def _validate_data(self, data):
        for k, v in data.items():
            if _is_scalar(v):
                raise TypeError("scalar values must be wrapped")

            if not isinstance(v, ManifestABC):
                raise TypeError("Non-scalar objects must be a ContextObject")

    def hashset(self):
        return ns_hashset(self.data)

    def __hash__(self):
        return hash(self.hashset())

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
    def from_ns(cls, ns, keys=None, mutable=False):
        """
        Will wrap a namespace and create ContextObjects that point to the
        object in kernel.
        """
        data = cls._wrap_context(ns, keys=keys)
        return cls(data, mutable=mutable)

    def keys(self):
        return self.data.keys()

    def items(self):
        return self.data.items()

    def values(self):
        return self.data.values()

    def __iter__(self):
        return iter(self.keys())

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        if not self.mutable:
            raise Exception("This ExecutionContext is immutable")

        if not isinstance(value, ManifestABC):
            raise TypeError("Must be ManifestABC")
        self.data[key] = value

    def extract(self):
        """
        Get the actual values from execution context
        """
        out = {}
        for k, v in self.data.items():
            out[k] = _obj(v)

        return out

    @property
    def key(self):
        bits = []
        for k in sorted(self.data):
            bits.append("{0}={1}".format(k, self.data[k]))
        _dict_string = ", ".join(bits)
        return _dict_string

    def __repr__(self):
        class_name = self.__class__.__name__
        key = self.key
        return "{class_name}({key})".format(**locals())
