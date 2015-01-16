import ast

from earthdragon.tools.timer import Timer

from naginpy.asttools import ast_source, _eval
from .manifest import Manifest, Expression, _manifest
from .exec_context import ExecutionContext

class Computable(object):
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

    def __repr__(self):
        return "Computable: " + self.expression.get_source() + " source_hash=" \
                + str(self.expression.key) + ' ns_hashset=' \
                + repr(self.context.hashset())


class ComputationManager(object):
    """
    Manages the relation because Manifests and their computed values.

    Note, all computables are Deferable, though that does not mean we 
    use this manager for deferment. 
    """

    def __init__(self):
        self.cache = {}
        self.value_map = {}

    def get(self, code, context):
        # trick to get hashable key
        manifest = _manifest(code, context)
        cache_entry = Computable(manifest)
        cache_entry = self.cache.setdefault(manifest, cache_entry)
        return cache_entry

    def value(self, source_hash, **kwargs):
        """
        Return the value returned by Manifest matching
        tuple(source_hash, context)

        This is only called by the getter_node.
        """
        context = ExecutionContext.from_ns(kwargs)
        key = tuple([source_hash, context])
        if key not in self.cache:
            raise Exception("Should not reach a cold cache"+str(key))
        entry = self.cache[key]
        return entry.value

    def by_value(self, val):
        """ Return the Computable by value """
        return self.value_map.get(id(val))

    def execute(self, entry, override=False):
        # execute if need be
        if not entry.executed or override:
            with Timer(verbose=False) as t:
                res = entry.manifest.eval()
            entry.value = res
            entry.exec_time = t.interval
            entry.executed = True
            self.value_map[id(entry.value)] = entry
        return entry.value

    def generate_getter_node(self, entry, context=None):
        """
        Given a Computable, we will return an AST node and namespace update
        that will result in grabbing the Computable.value.

        The namespace update dict should be the only additional context
        variables needed to plug in the Computed value.
        """

        context = entry.context
        source_hash = entry.expression.key

        return self._generate_getter_node(source_hash, context)

    def _generate_getter_node(self, source_hash, context):
        """
        This getter strategy replaces the expression with

        ```
        __defer_manager__.value(source_hash, key1=key1, key2=key, ...)
        ```

        The idea here is that the **kwargs will serve as the ExecutionContext
        during the lookup.
        """

        func = ast.Attribute(
            value=ast.Name(id="__defer_manager__", ctx=ast.Load()),
            attr="value", ctx=ast.Load()
        )
        args = [ast.Str(s=source_hash)]
        keywords = [ast.keyword(
            arg=k,
            value=ast.Name(id=k, ctx=ast.Load()))
            for k in context.keys()
        ]

        getter = ast.Call(func=func, args=args, keywords=keywords, 
                          starargs=None, kwargs=None)

        ns_update = {'__defer_manager__': self}
        return ast.fix_missing_locations(getter), ns_update



def _generate_getter_node(self, source_hash, context):
    """
    """
    func = ast.Attribute(
        value=ast.Name(id="__defer_manager__", ctx=ast.Load()),
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
