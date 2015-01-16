import ast
from functools import partial

from asttools import ast_repr, _eval

from ..graph import GatherGrapher
from .node_context import NodeContextManager


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


class SpecialEval(object):
    def __init__(self, grapher, ns, engines=None):
        # grapher might be source string or ast
        if isinstance(grapher, (ast.AST, str)):
            grapher = GatherGrapher(grapher)

        self.grapher = grapher
        self.ns = ns
        self.engines = engines
        self.context_manager = NodeContextManager(self.ns)
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

        for line in self.grapher.code.body:
            for engine in self.engines:
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
            self.handle_load_name(node, line, engine)

        engine.post_node_loop(line, ns)
        return

    def handle_load_name(self, node, line, engine):
        """
        For every Name(ctx=Load), we will walk up the AST and process as
        long as the Engine says it should.
        """
        grapher = self.grapher
        ns = self.ns
        # no child since load_names are leafs
        child = None
        while True:
            try:
                parent, field, field_index = grapher.parent(node)
                depth = grapher.depth[node]
            except:
                break

            if node in self.context_manager:
                context = self.context_manager.get(node)
            else:
                context = self.context_manager.create(node,
                                                    parent,
                                                    child,
                                                    field,
                                                    field_index,
                                                    line,
                                                    depth)

            # should should_handle_node and handle_node be merged into one?
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

    def sanity_check_objects(self, line):
        """
        Warn/Enforce the eval once semantic. If the object of an Attribute
        is grabbed via a NodeContext, that ast.Attribute should no longer be in
        line.

        We could either warn, error, or automatically replace the ast.Attribute

        HM. Auto replacing might be the way to go.
        """
        # TODO put object replacing logic into NormalEval
        for node in ast.walk(line):
            if node in self.context_manager.objects:
                if isinstance(node, ast.Name):
                    continue
