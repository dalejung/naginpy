from .. import defer
import imp;
imp.reload(defer)
from ..defer import *
from ..special_eval import SpecialEval

class Dale:
    def _handle_defer(self, type, arg, *args, **kwargs):
        if type == 'Attribute' and hasattr(self, arg):
            return True
        if type == 'Call' and arg == 'func':
            return True

    @property
    def tail(self, *args):
        return Op(self, 'tail')

class Op:
    def __init__(self, obj, name):
        self.obj = obj
        self.name = name

    def _handle_defer(self, type, arg, *args, **kwargs):
        if type == 'Call' and arg == 'func':
            return True

    def __repr__(self):
        return '{0}.{1}'.format(str(self.obj), self.name)

    def __call__(self, *args, **kwargs):
        return args


text = """
l = dale.tail(dale)
"""

code = ast.parse(text)

class DeferEval(SpecialEval):

    def should_handle(self, name, ns):
        val = ns.get(name.id, None)
        return isinstance(val, Dale)

    def handles_up(self, obj, node, parent, field):
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


dale = Dale()
ns = {
    'dale':dale
}

grapher = DeferEval(code, ns)
grapher.set_debug()
out = grapher.process()
print("\n".join(map(str, out)))

"""
for line in code.body:
    handle_line(grapher, line, is_deferred, ns)

locals().update(ns)

"""
