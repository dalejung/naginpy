import ast

from .graph import TriggerGrapher
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
            grapher = TriggerGrapher(grapher)

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
        for line in self.grapher.code.body:
            yield from filter(None, self.process_line(line))

    def __next__(self):
        return next(iter(self))

    def should_handle(self, node, ns=None):
        """
        Does this load_name var trigger special eval?
        """
        if ns is None:
            ns = self.ns
        raise NotImplementedError('Subclass needs to define should_handle')

    def process_line(self, line):
        grapher = self.grapher
        ns = self.ns

        yield self.debug(line, "Start Processing")

        if not line in grapher.trigger_nodes:
            res = _eval(line, ns)
            yield self.debug(line, "Evaled. No Trigger Nodes", res)
            return

        names = grapher.load_names[line]
        func = partial(is_deferred, ns=ns)
        deferred = list(filter(func, names))
        if not any(deferred):
            res = _eval(line, ns)
            yield self.debug(line, "Objects in namespace were unhandled", res)
            return

        print("Starting processing ", ast_repr(names)) 
        # these are the deferred
        for node in reversed(deferred):

            obj = ns[node.id]

            while True:
                try:
                    parent, field, i = grapher.parent(node)
                except:
                    print("Could not find parent for "+ast_repr(node))
                    break

                if obj is None:
                    break

                if not defer_handled(obj, node, parent, field):
                    break

                obj = _eval(parent, ns)
                print(obj)
                node = parent

            parent, field, i = grapher.parent(node)
            new_node = ast.Str(s=repr(obj), lineno=1, col_offset=3)
            replace_node(parent, field, i, new_node)
            print('done loop', ast_repr(node), ast.dump(node))
            print('done loop', ast_repr(parent), ast.dump(parent))

        obj = _eval(line, ns)
        return
        yield
