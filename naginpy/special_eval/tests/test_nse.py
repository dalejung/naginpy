import ast
from naginpy.asttools import ast_print

from ..special_eval import SpecialEval
from ..engine import Engine, NormalEval

class NSEEngine(Engine):
    def should_handle_line(self, line, load_names):
        return True

    def should_handle_node(self, node, context):
        parent = context.parent
        field = context.field

        handled = False
        if isinstance(parent, ast.Call) and field == 'func':
            handled = True

        if isinstance(parent, ast.Attribute) and field == 'value':
            handled = True

        if isinstance(node, ast.Call):
            handled = True

        print('*'*10)
        print(context.obj())
        ast_print('node:', node)
        ast_print('parent:', parent)
        print('field: ', field)
        print('handled :', handled)

        return handled

    def handle_node(self, node, context):
        if isinstance(node, ast.Call):
            for i, arg in enumerate(node.args):
                node.args[i] = ast.Str(s=arg.id, lineno=0, col_offset=3)
        return node


text = """
l = dale.tail(dale)
"""

class Dale(object):

    def tail(self, var):
        return var

dale = Dale()
ns = {}
ns['dale'] = dale

se = SpecialEval(text, ns=ns, engines=[NSEEngine(), NormalEval()])
out = se.process()

assert ns['l'] == 'dale'
