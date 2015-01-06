import ast

from naginpy.asttools import ast_source

def ns_hashkey(context):
    return frozenset({k: id(v) for k, v in context.items()}.items())


class CacheEntry(object):
    def __init__(self, code, context):
        self.code = code
        self.context = context
        self.value = None
        self.exec_time = None
        self.executed = False

    def source_hash(self):
        return hash(ast_source(self.code))

    def ns_hashkey(self):
        return ns_hashkey(self.context)

    def __hash__(self):
        return hash(tuple([self.source_hash(), self.ns_hashkey()]))

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
        return "CacheEntry: " + ast_source(self.code) + " source_hash=" \
                + str(self.source_hash()) + ' ns_hashkey=' \
                + repr(self.ns_hashkey())


class DeferManager(object):
    def __init__(self):
        self.cache = {}

    def get(self, code, context):
        # trick to get hashable key
        cache_entry = CacheEntry(code, context)
        cache_entry = self.cache.setdefault(cache_entry, cache_entry)
        return cache_entry

    def value(self, source_hash, **kwargs):
        key = tuple([source_hash, ns_hashkey(kwargs)])
        if key not in self.cache:
            raise Exception("Should not reach a cold cache"+str(key))
        entry = self.cache[key]
        return entry.value

    def generate_getter_node(self, source_hash, context=None):
        if isinstance(source_hash, str):
            source_hash = hash(source_hash)

        if isinstance(source_hash, CacheEntry):
            entry = source_hash
            context = entry.context
            source_hash = entry.source_hash()

        assert isinstance(source_hash, int)
        return self._generate_getter_node(source_hash, context)

    def _generate_getter_node(self, source_hash, context):

        func = ast.Attribute(
            value=ast.Name(id="defer_manager", ctx=ast.Load()),
            attr="value", ctx=ast.Load()
        )
        args = [ast.Num(n=source_hash)]
        keywords = [ast.keyword(
            arg=k,
            value=ast.Name(id=k, ctx=ast.Load()))
            for k in context.keys()
        ]

        getter = ast.Call(func=func, args=args, keywords=keywords, 
                          starargs=None, kwargs=None)
        return ast.fix_missing_locations(getter)
