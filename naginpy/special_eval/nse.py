"""
Non-Standard Evaluation
"""
import ast

from .engine import Engine
from ..asttools import ast_print, ast_source

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
                # TODO grab source from original source text
                str_rep = ast_source(arg)
                node.args[i] = ast.Str(s=str_rep, lineno=0, col_offset=3)
        return node
