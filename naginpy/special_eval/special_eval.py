import ast
from functools import partial

from ..graph import GatherGrapher
from ..asttools import ast_repr, _eval

_missing = object()

class EvalEvent(object):
    def __init__(self, code, msg, obj=None):
        self.code = code
        self.msg = msg
        self.obj = obj

    def __str__(self):
        return repr(self)

    def __repr__(self):
        msg = self.msg
        code_repr = ast_repr(self.code)
        obj = self.obj
        return "{code_repr} {msg} obj={obj}".format(**locals())

class ContextManager(object):
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

class NodeContext(object):
    """
    Note that child refers to the AST. So reverse what is intuitive.
    """
    # not every ast node has a referring python obj
    _invalid = object()

    def __init__(self, node, parent, child, field, line, ns, mgr):
        self.node = node
        self.parent = parent
        self.child = child
        self.field = field
        self.line = line
        self.ns = ns
        self.mgr = mgr

    def obj(self):
        return self.mgr.obj(self.node)


class SpecialEval(object):
    def __init__(self, grapher, ns, engines=None):
        # grapher might be source string or ast
        if isinstance(grapher, (ast.AST, str)):
            grapher = GatherGrapher(grapher)

        self.grapher = grapher
        self.ns = ns
        self.engines = engines
        self.context_manager = ContextManager(self.ns)
        self._debug = False

    def set_debug(self, debug=True):
        self._debug = debug

    def debug(self, code, msg, obj=None):
        if not self._debug:
            return
        return EvalEvent(code, msg, obj)

    def process(self):
        return list(self)


    # we only want to run once
    _iter = None

    def __iter__(self):
        if self._iter is None:
            self._iter = self._process()
        return self._iter

    def _process(self):
        if not self.grapher._processed:
            self.grapher.process()

        for engine in self.engines:
            for line in self.grapher.code.body:
                yield from filter(None, self.process_line(line, engine))

        self.sanity_check_objects(line)

        for engine in self.engines:
            res = engine.line_postprocess(line, self.ns)

    def __next__(self):
        return next(iter(self))

    def process_line(self, line, engine):
        grapher = self.grapher
        ns = self.ns
        # don't like this
        self.context_manager.engine = engine

        yield self.debug(line, "Start Processing")

        load_names = grapher.gather_nodes.get(line, None)

        if not engine.should_handle_line(line, load_names):
            yield self.debug(line, "{engine} does not handle line"
                             "".format(engine=repr(engine)))
            return

        for node in reversed(load_names):

            # no child since load_names are leafs
            child = None
            while True:
                try:
                    parent, field, i = grapher.parent(node)
                except:
                    break

                if node in self.context_manager:
                    context = self.context_manager.get(node)
                else:
                    context = self.context_manager.create(node,
                                                      parent,
                                                      child,
                                                      field,
                                                      line)
                if not engine.should_handle_node(node, context):
                    break

                new_node = engine.handle_node(node, context)

                if not isinstance(new_node, ast.AST) and new_node is not None:
                    raise Exception("Return handle_node should be None or"
                                    " ast.AST. Return same AST node for no op")

                # replace node value
                if new_node is not node:
                    parent, field, i = grapher.parent(node)
                    replace_node(parent, field, i, new_node)

                child = node
                node = parent

        return

    def sanity_check_objects(self, line):
        """
        Warn/Enforce the eval once semantic. If the object of an Attribute
        is grabbed via a NodeContext, that ast.Attribute should no longer be in
        line.

        We could either warn, error, or automatically replace the ast.Attribute

        HM. Auto replacing might be the way to go.
        """
        for node in ast.walk(line):
            if node in self.context_manager.objects:
                if isinstance(node, ast.Name):
                    continue
                print('boo',node)
