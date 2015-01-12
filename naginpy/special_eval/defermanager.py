import ast

from earthdragon.tools.timer import Timer

from naginpy.asttools import ast_source, _eval
from .manifest import Manifest, Expression
from .exec_context import ExecutionContext

def _manifest(code, context):
    expression = Expression(code)
    context = ExecutionContext.from_ns(context)
    manifest = Manifest(expression, context)
    return manifest

class CacheEntry(object):
    def __init__(self, manifest):
        self.manifest = manifest
        self.value = None
        self.exec_time = None
        self.executed = False

    @property
    def expression(self):
        return self.manifest.expression

    @property
    def context(self):
        return self.manifest.context

    def __eq__(self, other):
        if isinstance(other, CacheEntry):
            return hash(self) == hash(other)

        source_hash = other[0]
        ns_hashkey = other[1]

        if isinstance(source_hash, ast.AST):
            source_hash = ast_source(source_hash)

        if isinstance(source_hash, str):
            source_hash = hash(source_hash)

        if isinstance(ns_hashkey, dict):
            ns_hashkey = ns_hashkey(ns_hashkey)

        return self.source_hash() == source_hash \
                and self.ns_hashkey() == ns_hashkey

    def __repr__(self):
        return "CacheEntry: " + self.expression.get_source() + " source_hash=" \
                + str(self.expression.key) + ' ns_hashset=' \
                + repr(self.context.hashset())


class DeferManager(object):
    def __init__(self):
        self.cache = {}

    def get(self, code, context):
        # trick to get hashable key
        manifest = _manifest(code, context)
        cache_entry = CacheEntry(manifest)
        cache_entry = self.cache.setdefault(manifest, cache_entry)
        return cache_entry

    def value(self, source_hash, **kwargs):
        context = ExecutionContext.from_ns(kwargs)
        key = tuple([source_hash, context])
        if key not in self.cache:
            raise Exception("Should not reach a cold cache"+str(key))
        entry = self.cache[key]
        return entry.value

    def execute(self, entry, ns):
        with Timer(verbose=False) as t:
            res = entry.manifest.eval()
        entry.value = res
        entry.exec_time = t.interval
        entry.executed = True
        pass

    def generate_getter_node(self, entry, context=None):

        context = entry.context
        source_hash = entry.expression.key

        assert isinstance(source_hash, bytes) # md5 digest
        return self._generate_getter_node(source_hash, context)

    def _generate_getter_node(self, source_hash, context):

        func = ast.Attribute(
            value=ast.Name(id="defer_manager", ctx=ast.Load()),
            attr="value", ctx=ast.Load()
        )
        args = [ast.Bytes(s=source_hash)]
        keywords = [ast.keyword(
            arg=k,
            value=ast.Name(id=k, ctx=ast.Load()))
            for k in context.keys()
        ]

        getter = ast.Call(func=func, args=args, keywords=keywords, 
                          starargs=None, kwargs=None)
        return ast.fix_missing_locations(getter)
