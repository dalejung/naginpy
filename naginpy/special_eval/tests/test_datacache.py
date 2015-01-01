import ast
from collections import OrderedDict

from earthdragon.tools.timer import Timer

from naginpy.asttools import ast_print, ast_source, replace_node, _eval

from ..special_eval import SpecialEval
from ..engine import Engine, NormalEval

sections = []

def ns_hashkey(context):
    return frozenset({k: id(v) for k, v in context.items()})

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

class DataCacheEngine(Engine):
    def __init__(self, defer_manager):
        self.defer_manager = defer_manager

    def should_handle_line(self, line, load_names):
        return True

    def should_handle_node(self, node, context):
        parent = context.parent
        field = context.field

        handled = True
        if isinstance(parent, ast.Call) and field == 'func':
            handled = True

        verbose = False
        if verbose:
            print('*'*10)
            ast_print('node:', node)
            ast_print('parent:', parent)
            print('field: ', field)
            print('handled :', handled)

        return handled

    def handle_node(self, node, context):
        if isinstance(node, (ast.BinOp, ast.Call, ast.Subscript, ast.Compare)):
            if context not in sections:
                sections.append(context)
        return node

    def post_node_loop(self, line, ns):
        dm = self.defer_manager
        ns['defer_manager'] = dm
        is_load_name = lambda n: isinstance(n, ast.Name) \
                and isinstance(n.ctx, ast.Load)

        for context in sorted(sections, key=lambda x: x.depth, reverse=True):
            node = context.node

            names = set(n.id for n in filter(is_load_name, ast.walk(node)))
            ns_context = {k: ns[k] for k in names}

            entry = dm.get(node, ns_context)

            if not entry.executed:
                with Timer(verbose=False) as t:
                    res = _eval(entry.code, ns)
                entry.value = res
                entry.exec_time = t.interval
                entry.executed = True

            new_node = dm.generate_getter_node(entry)
            ast_print("AFSDFSD", new_node)
            replace_node(
                context.parent,
                context.field,
                context.field_index,
                new_node
            )

    def line_postprocess(self, line, ns):
        ast_print(line)


text = """
res = pd.rolling_sum(df, 5) + some_func(df.bob) + 1
#df = pd.DataFrame(np.random.randn(30, 3), columns=['a', 'bob', 'c'])
res2 = pd.rolling_sum(df, 5) + some_func(df.bob) + 1
"""
#res = df.bob + df.bob + 1
#pd.bob.rolling_sum(df + 1)

class Dale(object):

    def tail(self, var):
        return var

_count = 0
def some_func(df):
    print('some func')
    import time
    time.sleep(5)
    global _count
    _count += 1
    assert _count == 1
    return df

import pandas as pd
import numpy as np
df = pd.DataFrame(np.random.randn(30, 3), columns=['a', 'bob', 'c'])
dale = Dale()
ns = {}
ns['dale'] = dale
ns['pd'] = pd
ns['np'] = np
ns['df'] = df
ns['some_func'] = some_func
ns['_count'] = 0

dm = DeferManager()
dc = DataCacheEngine(dm)
se = SpecialEval(text, ns=ns, engines=[dc, NormalEval()])
out = se.process()

print('*'*10)
print('*'*10)
[ast_print(context.node) for context in sections]

context = list(sections)[0]

ast_print(se.grapher.code)
