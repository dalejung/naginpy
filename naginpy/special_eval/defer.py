import ast
from functools import partial

from asttools import ast_repr, ast_print, replace_node, _eval

def handles_defer(obj, node, parent, field):
    """
    Tests whether an object supports return back Deferreds.
    """

    handler = getattr(obj, '_handle_defer', None)
    if not handler:
        return False

    type, arg = None, None

    if isinstance(parent, ast.Attribute):
        type = 'Attribute'
        arg = parent.attr

    if isinstance(parent, ast.BinOp):
        type = 'BinOp'
        arg = parent.op.__class__.__name__

    if isinstance(parent, ast.Call):
        type = 'Call'
        arg = field

    if type is None:
        return False

    return obj._handle_defer(type, arg)

class DeferManager(object):
    pass


def handle_line(grapher, line, is_deferred, ns, eval_handler=None):
    if not line in grapher.trigger_nodes:
        _eval(line, ns)
        return

    names = grapher.trigger_nodes[line]
    func = partial(is_deferred, ns=ns)
    deferred = list(filter(func, names))
    if not any(deferred):
        _eval(line, ns)
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

            if not handles_defer(obj, node, parent, field):
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

def process_triggered(self, triggered, line):
    grapher = self.grapher
    ns = self.ns

    for node in reversed(triggered):
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
