import ast

from naginpy.asttools import ast_repr

_missing = object()

class NodeContext(object):
    """
    Note that child refers to the AST. So reverse what is intuitive.
    """
    # not every ast node has a referring python obj
    _invalid = object()

    def __init__(self, node, parent, child, field, field_index, line, depth,
                 ns, mgr):
        self.node = node
        self.parent = parent
        self.child = child
        self.field = field
        self.field_index = field_index
        self.line = line
        self.depth = depth
        self.ns = ns
        self.mgr = mgr

    def obj(self):
        return self.mgr.obj(self.node)

class NodeContextManager(object):
    def __init__(self, ns):
        self.ns = ns
        self.contexts = {}
        self.objects = {}
        self.engine = None

    def __contains__(self, key):
        return key in self.contexts

    def get(self, node):
        return self.contexts[node]

    def create(self, *args, **kwargs):
        node = args[0]
        if node in self.contexts:
            raise Exception("We already have this node context, something wrong?")
        kwargs['ns'] = self.ns
        kwargs['mgr'] = self
        context = NodeContext(*args, **kwargs)
        self.contexts[node] = context
        return context

    def obj(self, node):
        """
        Grab the value corresponding to this node. 
        Name(id=id, ctx=Load): var in namespace
        Attribute(): attribute of var in namespace
        Call(): result of call

        Note:
            So what I would prefer is for attribute access to never occur
            twice, since python is so dynamic.

            However, while I can prevent the NodeContext system from not
            accessing twice, the corresponding engine would have to
            replace the Attribute node.

            So I'm not sure if there's a good way to enforce my access once
            mandate globally. More like coordination it seems.
        """
        assert self.engine is not None, 'Engine should be set before obj called'
        obj = self._obj(node)
        if obj is _missing and not self.engine._allow_missing:
            raise NameError("context.obj() not found for "
                            "{0}".format(ast_repr(node)))
        return obj

    def _obj(self, node):
        if node in self.objects:
            obj = self.objects[node]

        obj = NodeContext._invalid
        if isinstance(node, ast.Name):
            obj = self.ns.get(node.id, _missing)

        if isinstance(node, ast.Attribute):
            child_obj = self.get(node.value).obj()
            obj = getattr(child_obj, node.attr)

        self.objects[node] = obj
        return obj

