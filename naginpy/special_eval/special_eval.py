import ast
from functools import partial

from .graph import GatherGrapher
from .asttools import ast_repr, _eval

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
    def __init__(self, grapher, ns):
        # grapher might be source string or ast
        if isinstance(grapher, (ast.AST, str)):
            grapher = GatherGrapher(grapher)

        self.grapher = grapher
        self.ns = ns
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
            yield from filter(None, self.process_line(line))

    def __next__(self):
        return next(iter(self))

    def should_handle(self, node, ns=None):
        """
        Does this load_name var gather special eval?
        """
        if ns is None:
            ns = self.ns
        raise NotImplementedError('Subclass needs to define should_handle')

    def process_line(self, line):
        grapher = self.grapher
        ns = self.ns

        yield self.debug(line, "Start Processing")

        if not line in grapher.gather_nodes:
            res = _eval(line, ns)
            yield self.debug(line, "Evaled. No gather Nodes", res)
            return

        nodes = grapher.gather_nodes[line]
        func = partial(self.should_handle, ns=ns)

        triggered = list(filter(func, nodes))
        if not any(triggered):
            res = _eval(line, ns)
            yield self.debug(line, "Objects in namespace were unhandled", res)
            return

        yield self.debug(line, "Handling triggered nodes")

        self.process_triggered(triggered, line)
        self.cleanup_line(line)

    def cleanup_line(self, line):
        ns = self.ns
        obj = _eval(line, ns)
        return obj

    def handle_up(self, obj, node, parent, field):
        return False

    def process_triggered(self, triggered, line):
        grapher = self.grapher
        ns = self.ns

        for node in reversed(triggered):
            pass

    def _process_trigger(self, obj, node):
            obj = ns[node.id]

            # climb up
            while True:
                try:
                    parent, field, i = grapher.parent(node)
                except:
                    print("Could not find parent for "+ast_repr(node))
                    break

                if obj is None:
                    break

                if not self.handle_up(obj, node, parent, field):
                    break

                obj = _eval(parent, ns)
                node = parent

            parent, field, i = grapher.parent(node)
            new_node = ast.Str(s=repr(obj), lineno=1, col_offset=3)
            replace_node(parent, field, i, new_node)
