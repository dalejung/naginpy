import ast
from collections import OrderedDict

from earthdragon.tools.timer import Timer

from naginpy.asttools import ast_print, ast_source, replace_node, _eval

from ..special_eval import SpecialEval
from ..engine import Engine, NormalEval

sections = OrderedDict()

def ns_hashkey(context):
    return tuple([(k, id(v)) for k, v in context.items()])

class CacheEntry(object):
    def __init__(self, code, context):
        self.code = code
        self.context = context
        self.value = None
        self.exec_time = None
        self.executed = False

    def __hash__(self):
        return hash(ns_hashkey(self.context)) + hash(ast_source(self.code))

    def __eq__(self, other):
        if isinstance(other, CacheEntry):
            return hash(self) == hash(other)
        # assume tuple(code, context)
        return ast_source(sef.code) == ast_source(other[0]) \
                and hash(ns_hashkey(self.context)) == ns_hashkey(other[1])

    def __repr__(self):
        return "CacheEntry: " + ast_source(self.code)

class DeferManager(object):
    def __init__(self):
        self.cache = {}

    def get(self, code, context):
        # trick to get hashable key
        cache_entry = CacheEntry(code, context)
        cache_entry = self.cache.setdefault(cache_entry, cache_entry)
        return cache_entry

    def value(self, source, **kwargs):
        print(source, kwargs)

    def generate_getter_node(self, source, context):
        func = ast.Attribute(
            value=ast.Name(id="defer_manager", ctx=ast.Load()),
            attr="value", ctx=ast.Load()
        )
        args = [ast.Num(n=hash(source))]
        keywords = [ast.keyword(
            arg=k,
            value=ast.Name(id=k, ctx=ast.Load()))
            for k in context.keys()
        ]

        getter = ast.Call(func=func, args=args, keywords=keywords, 
                          starargs=None, kwargs=None)
        return ast.fix_missing_locations(getter)


dm = DeferManager()
blah = ast.parse("defer_manager.value(123423214132, bob=bob, frank=frank)")
func = dm.generate_getter_node("dale", {'hi':'hi'})

_eval(func, {'defer_manager':dm, 'hi':'hi2'})

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
            if node not in sections:
                sections[node] = context
        return node

    def post_node_loop(self, line, ns):
        ns['defer_manager'] = self.defer_manager
        is_load_name = lambda n: isinstance(n, ast.Name) \
                and isinstance(n.ctx, ast.Load)

        for node, context in sections.items():
            names = set(n.id for n in filter(is_load_name, ast.walk(node)))
            ns_context = {k: ns[k] for k in names}
            entry = self.defer_manager.get(node, ns_context)
            with Timer(verbose=False) as t:
                _eval(entry.code, ns)
            entry.exec_time = t.interval
            entry.executed = True


    def line_postprocess(self, line, ns):
        ast_print(line)


text = """
res = pd.rolling_sum(df.iloc[df.a > df.bob.tail()], 5)
"""
#pd.bob.rolling_sum(df + 1)

class Dale(object):

    def tail(self, var):
        return var

import pandas as pd
import numpy as np
df = pd.DataFrame(np.random.randn(3,3), columns=list('abc'))
dale = Dale()
ns = {}
ns['dale'] = dale
ns['pd'] = pd
ns['df'] = df

dc = DataCacheEngine(DeferManager())
se = SpecialEval(text, ns=ns, engines=[dc])
out = se.process()

print('*'*10)
print('*'*10)
[ast_print(node) for node, context in sections.items()]

node = list(sections.values())[0]
