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

class SpecialEval(object):
    def __init__(self, grapher, ns, engines=None):
        # grapher might be source string or ast
        if isinstance(grapher, (ast.AST, str)):
            grapher = GatherGrapher(grapher)

        self.grapher = grapher
        self.ns = ns
        self.engines = engines
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

    def __next__(self):
        return next(iter(self))

    def process_line(self, line, engine):
        grapher = self.grapher
        ns = self.ns

        yield self.debug(line, "Start Processing")

        load_names = grapher.gather_nodes.get(line, None)

        if not engine.should_handle_line(line, load_names):
            yield self.debug(line, "{engine} does not handle line"
                             "".format(engine=repr(engine)))
            return

        for node in reversed(load_names):
            obj = ns.get(node.id, _missing)

            while True:
                try:
                    parent, field, i = grapher.parent(node)
                except:
                    break

                if not engine.should_handle_node(obj, node, parent, field, line):
                    break

                new_node = engine.handle_node(obj, node, parent, field, line)

                if not isinstance(new_node, ast.AST) and new_node is not None:
                    raise Exception("Return handle_node should be None or"
                                    " ast.AST. Return same AST node for no op")

                # replace node value
                if new_node is not node:
                    parent, field, i = grapher.parent(node)
                    replace_node(parent, field, i, new_node)
                node = parent


        res = engine.line_postprocess(line, ns)
        return
